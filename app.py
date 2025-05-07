# app.py

import streamlit as st
import pandas as pd
from db.db_connector import get_connection
from scripts.forecasting import forecast_expenses
import plotly.express as px

st.set_page_config("Finance Dashboard", layout="wide")
st.title(" Personal Finance Manager")

# --- Database connection ---
conn = get_connection()
cursor = conn.cursor()

# --- Create Table if not exists ---
cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    Date DATE,
    Description VARCHAR(255),
    Amount FLOAT,
    Type VARCHAR(10),
    Category VARCHAR(50)
)
""")
conn.commit()

# --- Data Fetching ---
def fetch_data():
    cursor.execute("SELECT * FROM transactions")
    rows = cursor.fetchall()
    return pd.DataFrame(rows, columns=["ID", "Date", "Description", "Amount", "Type", "Category"])

# --- UI to Add Transaction ---
st.sidebar.header("➕ Add Transaction")
with st.sidebar.form("add_form"):
    date = st.date_input("Date")
    desc = st.text_input("Description")
    amt = st.number_input("Amount")
    typ = st.selectbox("Type", ["Income", "Expense"])
    cat = st.text_input("Category")
    submit = st.form_submit_button("Add")
    if submit:
        cursor.execute("INSERT INTO transactions (Date, Description, Amount, Type, Category) VALUES (%s, %s, %s, %s, %s)", 
                       (date, desc, amt, typ, cat))
        conn.commit()
        st.success("Transaction added!")

# --- Data Display ---
df = fetch_data()
st.subheader(" All Transactions")
st.dataframe(df)

# --- Update/Delete ---
st.sidebar.header("🛠 Modify Transaction")
id_to_mod = st.sidebar.number_input("Transaction ID", min_value=1, step=1)
if st.sidebar.button("Delete"):
    cursor.execute("DELETE FROM transactions WHERE id=%s", (id_to_mod,))
    conn.commit()
    st.sidebar.success("Deleted.")
if st.sidebar.button("Update Description to 'Updated Entry'"):
    cursor.execute("UPDATE transactions SET Description=%s WHERE id=%s", ('Updated Entry', id_to_mod))
    conn.commit()
    st.sidebar.success("Updated.")

# --- Visual Dashboard ---
df['Date'] = pd.to_datetime(df['Date'])

col1, col2 = st.columns(2)

with col1:
    st.markdown("###  Monthly Income vs Expenses")
    summary = df.groupby([df['Date'].dt.to_period('M'), 'Type'])['Amount'].sum().unstack().fillna(0)
    st.bar_chart(summary)

with col2:
    st.markdown("###  Category-wise Spending")
    expense_df = df[df['Type'] == 'Expense']
    cat_sum = expense_df.groupby('Category')['Amount'].sum()
    fig = px.pie(cat_sum, names=cat_sum.index, values=cat_sum.values)
    st.plotly_chart(fig)

st.markdown("###  Forecasted Expenses (Next 3 Months)")
forecast = forecast_expenses(df)
st.line_chart(forecast)

st.markdown("###  Savings Over Time")
monthly = df.copy()
monthly['Amount'] = monthly.apply(lambda x: x['Amount'] if x['Type'] == 'Income' else -abs(x['Amount']), axis=1)
savings = monthly.resample('M', on='Date')['Amount'].sum().cumsum()
st.area_chart(savings)
