#!/usr/bin/env python

import pandas as pd
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

creds = service_account.Credentials.from_service_account_file('secrets/sheets_credentials.json')
SPREADSHEET_ID = '1hS045fKK5xA6CJsRq0G2Z_Uk4s_7BPJqwQGA4wngAOI'
RANGE_NAME = 'Sheet1!A1'

# Load your CSV file
csv_file = sys.argv[1]
data = pd.read_csv(csv_file)

# Connect to Google Sheets API
service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

# Convert dataframe to a list of lists for API upload
values = [data.columns.tolist()] + data.values.tolist()

# Prepare the data for upload
body = {'values': values}

# Clear existing content and update the sheet
sheet.values().clear(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
sheet.values().update(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME, 
                      valueInputOption='RAW', body=body).execute()

print('CSV data uploaded successfully.')

# range_name = f'{SPREADSHEET_ID}!A2:A'
# # Set date formatting
# requests = [
#     {
#         "repeatCell": {
#             "range": {
#                 "sheetId": 0,  # Replace with your sheet ID if different
#                 "startRowIndex": 1,  # Adjust as needed
#                 "startColumnIndex": 0,  # Column A
#                 "endColumnIndex": 1
#             },
#             "cell": {
#                 "userEnteredFormat": {
#                     "numberFormat": {
#                         "type": "DATE",
#                         "pattern": "dd/MMM/yyyy HH:mm:ss"  # Adjust to your preferred format
#                     }
#                 }
#             },
#             "fields": "userEnteredFormat.numberFormat"
#         }
#     }
# ]

# # Send the formatting request
# batch_update_request = {'requests': requests}
# r = service.spreadsheets().batchUpdate(
#     spreadsheetId=SPREADSHEET_ID,
#     body=batch_update_request
# ).execute()
# # print(r)
# print("Date-time column formatted successfully.")

