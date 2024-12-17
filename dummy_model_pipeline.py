import pandas as pd

def read_data():
    input_data = pd.read_excel(r"C:\Users\NC3589\DELFI3\data\preprocessed.xlsx", index_col=0, parse_dates=True)
    input_data[['res_C15', 'res_YBBPM15']] = 0
    return input_data

def construct_forecasts(input_data):
    output_var = (input_data['C15'] + input_data['res_C15'] + input_data['YBBPM15'] + input_data['res_YBBPM15'])
    return output_var

input_data = read_data()
output_var = construct_forecasts(input_data=input_data)
output_var.plot()