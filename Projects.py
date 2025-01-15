#Project page allow the user to create, manage, and set timelines for a rfp response 
#in such a way that allows for a comprehesive experience and managed expectation for all 
#response team members
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import sqlite3
import os

data_dir = "c:\\CATarina\\data\\"

#creating a SQL Lite database to store projects and state of work for proposal management

conn = sqlite3.connect("projects_database")
c = conn.cursor()

c.execute(
    """
    CREATE TABLE IF NOT EXISTS projects
        ([project_id] INTEGER PRIMARY KEY,
         [project_name] TEXT,
         [due_date] DATETIME,
         [status] TEXT,
         [team] TEXT,
         [directory] TEXT)
    """
)

conn.commit()

sql_query = pd.read_sql_query(
    """
    SELECT
    project_name, due_date, status, team, directory
    FROM projects
    """,
    conn,
)

df = pd.DataFrame(sql_query, columns=["project_name", "due_date", "status", "team", "directory"])

df['due_date'] = pd.to_datetime(df['due_date'])

conn.close()

st.title('CATarina Project List')

def create_project_dir(dirname):
    #create the directory on the file system
    try:
        os.makedirs(dirname)
    except:
        st.error("A project with this name already exists. Please pick a unique name for each project.")
    
def df_on_change(df):
    state = st.session_state["edited_df"]
    for index, updates in state["edited_rows"].items():
        st.session_state["df"].loc[st.session_state["df"].index == index, "edited"] = True
        if 'project_name' in updates:
            project_name = updates['project_name'] 
            project_dir = data_dir + project_name
            st.session_state["df"].loc[st.session_state["df"].index == index, "directory"] = project_dir
            create_project_dir(project_dir)
        for key, value in updates.items():
            st.session_state["df"].loc[st.session_state["df"].index == index, key] = value
    for row in state["added_rows"]:
        if 'project_name' in row:
            project_name = row['project_name'] 
            project_dir = data_dir + project_name
            new_row={'project_name':project_name, 'status':'New',  'directory': project_dir}
            st.session_state["df"] =  st.session_state["df"]._append(new_row, ignore_index=True)
            create_project_dir(project_dir)

    for row in state["deleted_rows"]:
        st.session_state["df"] = st.session_state["df"].drop(row)

    dbcon = sqlite3.connect("projects_database")
    st.session_state["df"].to_sql('projects', dbcon, if_exists='replace', index=False) #save to our database
    dbcon.commit()
    dbcon.close()

def create_edit_frame():
    if "df" not in st.session_state:
        st.session_state["df"] = df
    edf = st.data_editor(st.session_state["df"], num_rows="dynamic", on_change=df_on_change, args=[df], column_config={
            "project_name": "Project",
            "due_date": st.column_config.DatetimeColumn("Due Date", format='MM/DD/YYYY'),
            "status": st.column_config.SelectboxColumn("Status", options=["New", "In Progress", "Complete", "No Bid"], default= "New"),
            "team": st.column_config.SelectboxColumn("Team", options=["EMC", "FIN", "HED", "PMC"]),
            "directory": st.column_config.LinkColumn("Directory",  default = data_dir + "create-new",disabled=True, display_text ="Open")
        },
        key="edited_df",
        hide_index=True
        )
    return edf

edited_df = create_edit_frame()


    

    

    

