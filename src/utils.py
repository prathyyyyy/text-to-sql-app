from __future__ import annotations
import os, sys
import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
import sqlparse
from collections import OrderedDict, Counter
from databricks import sql
from databricks import sql as dbsql

import streamlit_authenticator as stauth
import textwrap

import os
import re
from contextlib import contextmanager
from typing import Dict, Iterable, List
import streamlit.components.v1 as components

import yaml
from yaml.loader import SafeLoader
from dotenv import load_dotenv
load_dotenv()

# LLM libraries
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.chains.llm import LLMChain
from langchain_openai import ChatOpenAI


@st.cache_data
def load_user_query_history(user_name):
    # Getting the sample details of the selected table
    conn = sql.connect(server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME"),
                    http_path       = os.getenv("DATABRICKS_HTTP_PATH"),
                    access_token    = os.getenv("DATABRICKS_ACCESS_TOKEN"))

    query = f"SELECT * FROM workspace.sqlgenpro_user_query_history.query_history WHERE user_name = '{user_name}' AND timestamp > current_date - 20"
    df = pd.read_sql(sql=query,con=conn)
    return df


# Function to list all the catalog, schema and tables present in the database
@st.cache_data
def list_catalog_schema_tables():
    with sql.connect(server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME"),
                    http_path       = os.getenv("DATABRICKS_HTTP_PATH"),
                    access_token    = os.getenv("DATABRICKS_ACCESS_TOKEN")) as connection:
        with connection.cursor() as cursor:
            # cursor.catalogs()
            # result_catalogs = cursor.fetchall()

            # cursor.schemas()
            # result_schemas = cursor.fetchall()

            cursor.tables()
            result_tables = cursor.fetchall()

            return result_tables


@st.cache_data
def get_enriched_database_schema(catalog: str, schema: str, tables_list: list) -> str:
    """
    For each table in the provided list, this function:
    1. Retrieves the CREATE TABLE statement.
    2. Describes the table (columns and datatypes).
    3. Identifies categorical string columns (<= 20 unique values).
    4. Samples a few rows.

    Returns
    -------
    table_schema : str
        Concatenated schema, sample rows, and categorical fields for each table.
    """
    table_schema = ""

    for table in tables_list:
        # Always use backquotes for catalog.schema.table
        full_table_name = f"`{catalog}`.`{schema}`.`{table}`"

        # Open Databricks SQL connection
        conn = sql.connect(
            server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_ACCESS_TOKEN"),
        )

        # -------------------------
        # 1. Get CREATE TABLE
        # -------------------------
        query = f"SHOW CREATE TABLE {full_table_name}"
        df = pd.read_sql(sql=query, con=conn)
        stmt = df["createtab_stmt"][0].split("USING")[0]

        # -------------------------
        # 2. Get Column Info
        # -------------------------
        query = f"DESCRIBE TABLE {full_table_name}"
        df = pd.read_sql(sql=query, con=conn)
        string_cols = df[df["data_type"] == "string"]["col_name"].tolist()

        # -------------------------
        # 3. Get categorical columns (<= 20 distinct values)
        # -------------------------
        sql_distinct = " UNION ALL ".join(
            [
                f"SELECT '{col}' AS column_name, COUNT(DISTINCT {col}) AS cnt, "
                f"ARRAY_AGG(DISTINCT {col}) AS values FROM {full_table_name}"
                for col in string_cols
            ]
        )

        if sql_distinct:
            df_categories = pd.read_sql(sql=sql_distinct, con=conn)
            df_categories = df_categories[df_categories["cnt"] <= 20].drop(columns="cnt")
            df_categories_string = (
                "No Categorical Fields"
                if df_categories.empty
                else df_categories.to_string(index=False)
            )
        else:
            df_categories_string = "No String Fields"

        # -------------------------
        # 4. Sample rows
        # -------------------------
        query = f"SELECT * FROM {full_table_name} LIMIT 3"
        df = pd.read_sql(sql=query, con=conn)
        sample_rows = df.to_string(index=False)

        # -------------------------
        # Combine
        # -------------------------
        if table_schema == "":
            table_schema = (
                    stmt
                    + "\n"
                    + sample_rows
                    + "\n\nCategorical Fields:\n"
                    + df_categories_string
                    + "\n"
            )
        else:
            table_schema += (
                    "\n"
                    + stmt
                    + "\n"
                    + sample_rows
                    + "\n\nCategorical Fields:\n"
                    + df_categories_string
                    + "\n"
            )

    return table_schema


def process_llm_response_for_mermaid(response: str) -> str:
    """
    Extracts Mermaid code block from the LLM response.
    """
    start_idx = response.find("```mermaid") + len("```mermaid")
    end_idx = response.find("```", start_idx)
    return response[start_idx:end_idx].strip()


def process_llm_response_for_sql(response: str) -> str:
    """
    Extracts SQL code block from the LLM response.
    """
    start_idx = response.find("```sql") + len("```sql")
    end_idx = response.find("```", start_idx)
    return response[start_idx:end_idx].strip()


def mermaid(code: str) -> None:
    """
    Render a Mermaid diagram inside Streamlit with scroll support.
    """
    code_escaped = code.replace("\\", "\\\\").replace("`", "\\`")

    components.html(
        f"""
        <div id="mermaid-container" 
             style="width: 105%; height: 700px; overflow: auto; border: 1px solid #ddd; border-radius: 8px; background-color: #fff;">
            <pre class="mermaid" style="min-width: 600px; min-height: 800px;">
                {code_escaped}
            </pre>
        </div>

        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true }});
        </script>
        """,
        height=800,
    )



# ==============================
# Main ERD Diagram Generator
# ==============================


@st.cache_data
def create_erd_diagram(catalog: str, schema: str, tables_list: list) -> str:
    """
    Creates an ERD diagram using Mermaid code.

    Steps:
    1. Extracts column schema of selected tables.
    2. Prepares a natural language prompt with schema details.
    3. Invokes an LLM to generate Mermaid ERD code.

    Returns
    -------
    output : str
        Mermaid diagram code generated by LLM.
    """
    table_schema = {}

    for table in tables_list:
        full_table_name = f"`{catalog}`.`{schema}`.`{table}`"

        conn = sql.connect(
            server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_ACCESS_TOKEN"),
        )

        query = f"DESCRIBE TABLE {full_table_name}"
        df = pd.read_sql(sql=query, con=conn)
        cols = df["col_name"].tolist()
        col_types = df["data_type"].tolist()
        table_schema[table] = [f"{c} : {t}" for c, t in zip(cols, col_types)]

    # -------------------------
    # Prepare prompt for LLM
    # -------------------------
    template_string = """ 
    You are an expert in creating ERD diagrams (Entity Relationship Diagrams) for databases. 
    You have been given the task to create an ERD diagram for the selected tables in the database. 
    The ERD diagram should contain the tables and the columns present in the tables. 
    You need to generate the Mermaid code for the complete ERD diagram.
    Make sure the ERD diagram is clear and easy to understand with proper relationships details.

    The selected tables in the database are given below (delimited by ##) in dictionary format:
    Keys = table names, Values = list of columns with datatype.

    ##
    {table_schema}
    ##

    Validate the Mermaid code before returning.
    Give me the final Mermaid code for the ERD diagram.
    """

    prompt_template = PromptTemplate.from_template(template_string)

    llm_chain = LLMChain(
        llm=ChatOpenAI(model="gpt-5-mini", temperature=0),
        prompt=prompt_template,
    )

    response = llm_chain.invoke({"table_schema": table_schema})
    return response["text"]


@st.fragment
@st.cache_data
def quick_analysis(table_schema):
    ### Defining the output schema from the LLM
    output_schema = ResponseSchema(name="quick_analysis_questions",
                                   description="Generated Quick Analysis questions for the given tables list")
    output_parser = StructuredOutputParser.from_response_schemas([output_schema])
    format_instructions = output_parser.get_format_instructions()

    ### Defining the prompt template
    template_string = """
    Using the provided SCHEMA (delimited by ##), generate the top 5 "quick analysis" questions based on the relationships between the tables which can be answered by creating a Databricks SQL code. 
    These questions should be practical and insightful, targeting the kind of business inquiries a product manager or analyst would typically investigate daily.    

    SCHEMA:
    ##
    {table_schema}
    ##

    The output should be in a nested JSON format with the following structure:
    {fomat_instructions}
     """

    prompt_template = PromptTemplate.from_template(template_string)

    ### Defining the LLM chain
    llm_chain = LLMChain(
        llm=ChatOpenAI(model="gpt-5", temperature=0),
        prompt=prompt_template,
        output_parser=output_parser
    )

    response = llm_chain.invoke({"table_schema": table_schema, "fomat_instructions": format_instructions})
    # output = response['text']

    return response

@st.fragment
@st.cache_data
def create_sql(question,table_schema):

    ### Defining the prompt template
    template_string = """ 
    You are a expert data engineer working with a Databricks environment.\
    Your task is to generate a working SQL query in Databricks SQL dialect. \
    During join if column name are same please use alias ex llm.customer_id \
    in select statement. It is also important to respect the type of columns: \
    if a column is string, the value should be enclosed in quotes. \
    If you are writing CTEs then include all the required columns. \
    While concatenating a non string column, make sure cast the column to string. \
    For date columns comparing to string , please cast the string input.\
    For string columns, check if it is a categorical column and only use the appropriate values provided in the schema.\

    SCHEMA:
    ## {table_schema} ##

    QUESTION:
    ##
    {question}
    ##


    IMPORTANT: MAKE SURE THE OUTPUT IS JUST THE SQL CODE AND NOTHING ELSE. Ensure the appropriate CATALOG is used in the query and SCHEMA is specified when reading the tables.
    ##

    OUTPUT:
    """
    prompt_template = PromptTemplate.from_template(template_string)

    ### Defining the LLM chain
    llm_chain = LLMChain(
        llm=ChatOpenAI(model="gpt-5",temperature=0),
        prompt=prompt_template
    )

    response = llm_chain.invoke({"question":question,"table_schema":table_schema})
    output = response['text']

    return output


@st.fragment
@st.cache_data
def create_advanced_sql(question,sql_code,table_schema):

    ### Defining the prompt template
    template_string = """ 
    You are a expert data engineer working with a Databricks environment.\
    Your task is to generate a working SQL query in Databricks SQL dialect. \
    Enclose the complete SQL_CODE in a WITH clause and name it as MASTER. DON'T ALTER THE given SQL_CODE. \
    Then based on the QUESTION and the master WITH clause, generate the final SQL query based on the WITH clause.\
    ONLY IF additional information is needed to answer the QUESTION, then use the SCHEMA to join the details to get the final answer. \


    INPUT:
    SQL_CODE:
    ##
    {sql_code}
    ##

    SCHEMA:
    ## {table_schema} ##

    QUESTION:
    ##
    {question}
    ##

    IMPORTANT: MAKE SURE THE OUTPUT IS JUST THE SQL CODE AND NOTHING ELSE.
    ##


    OUTPUT:
    """
    prompt_template = PromptTemplate.from_template(template_string)

    ### Defining the LLM chain
    llm_chain = LLMChain(
        llm=ChatOpenAI(model="gpt-5",temperature=0),
        prompt=prompt_template
    )

    response = llm_chain.invoke({"sql_code":sql_code,"question":question,"table_schema":table_schema})
    output = response['text']

    return output

# Function to load data from the database given the SQL query
def load_data_from_query(query: str) -> pd.DataFrame:
    # Normalize: trim and drop anything before a valid SQL keyword if present
    q = query.strip()
    if not re.match(r'(?is)^(with|select|insert|update|delete|merge|create|drop|alter)\b', q):
        m = re.search(r'(?is)(with|select|insert|update|delete|merge|create|drop|alter)\b', q)
        if m:
            q = q[m.start():]  # recover from accidental leading junk like 'T '

    with sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_ACCESS_TOKEN"),
    ) as conn:
        df = pd.read_sql(sql=q, con=conn)
    return df


# Function to validate if self-correction is needed for the generated SQL query
@st.fragment
def self_correction(query):
    error_msg = ""

    try:
        df = load_data_from_query(query)
        # print(df.shape)
        # df.head()
        error_msg += "Successful"
    except Exception as e:
        error_msg += str(e)

    if error_msg == "Successful":
        return error_msg
    else:
        # print("There is error")
        # print(error_msg)
        return error_msg


# Function to validate and self-correct generated SQL query
@st.fragment
def correct_sql(question, sql_code, table_schema, error_msg):
    ### Defining the prompt template
    template_string = """ 
    You are a expert data engineer working with a Databricks environment.\
    Your task is to modify the SQL_CODE using Databricks SQL dialect based on the QUESTION, SCHEMA and the ERROR_MESSAGE. \
    If ERROR_MESSAGE is provided, then make sure to correct the SQL query according to that. \

    SCHEMA:
    ## {table_schema} ##

    ERROR_MESSAGE:
    ## {error_msg} ##

    SQL_CODE:
    ##
    {sql_code}

    QUESTION:
    ## {question} ##

    ##


    IMPORTANT: MAKE SURE THE OUTPUT IS JUST THE SQL CODE AND NOTHING ELSE. Ensure the appropriate CATALOG is used in the query and SCHEMA is specified when reading the tables.
    ##

    OUTPUT:
    """
    prompt_template = PromptTemplate.from_template(template_string)

    ### Defining the LLM chain
    llm_chain = LLMChain(
        llm=ChatOpenAI(model="gpt-5", temperature=0),
        prompt=prompt_template
    )

    response = llm_chain.invoke(
        {"question": question, "sql_code": sql_code, "table_schema": table_schema, "error_msg": error_msg})
    output = response['text']

    return output


def validate_and_correct_sql(question, query, table_schema):
    error_msg = self_correction(query)

    if error_msg == "Successful":
        # print("Query is successful")
        return "Correct", query
    else:
        modified_query = correct_sql(question, query, table_schema, error_msg=error_msg)
        return "Incorrect", modified_query


def _sql_str(s: str) -> str:
    return s.replace("'", "''") if s is not None else ""

def add_to_user_history(user_name, question, query_text, favourite_ind: bool):
    conn = sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_ACCESS_TOKEN"),
    )
    try:
        table = "workspace.sqlgenpro_user_query_history.query_history"
        fav_literal = "true" if favourite_ind else "false"  # <-- boolean literal for SQL

        stmt = (
            f"INSERT INTO {table} (user_name, timestamp, question, query, favorite) VALUES ("
            f"'{_sql_str(user_name)}', current_timestamp(), "
            f"'{_sql_str(question)}', '{_sql_str(query_text)}', {fav_literal})"
        )

        with conn.cursor() as cur:
            cur.execute(stmt)
    finally:
        conn.close()
