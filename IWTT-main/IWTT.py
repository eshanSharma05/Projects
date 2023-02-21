import streamlit
import streamlit as st
import pandas as pd
import os
import numpy as np
from geopy.distance import geodesic
from datetime import datetime
import xlsxwriter
import re
from io import BytesIO

outputDeficit = BytesIO()
outputExcess = BytesIO()
outputPaths = BytesIO()

allWarehouse=None
limit=''
mon=6
qpbmDF = pd.DataFrame()
amcDF = pd.DataFrame()
tsnDF = pd.DataFrame()
codes = []
wh = []
choice=''
distanceMatrix = pd.DataFrame()
flagForWarehouse = False
outputDF=pd.DataFrame(columns=["From Warehouse","Consumption(amc)","Total Stock","Excess Quantity","To Warehouse","Deficit Quantity","Actually Transferred","Code","Distance","Quantity Per Box Mapping"])
outputEx=pd.DataFrame(columns=["From Warehouse","Consumption(amc)","Total Stock","Excess Quantity","Quantity Left","To Warehouse","Deficit Quantity","Actually Transferred","Code","Distance","Quantity Per Box Mapping"])
outputPath=pd.DataFrame(columns=["Base Location","From Warehouse","Start","Consumption(amc)","Total Stock","Excess Quantity Left","To Warehouse","Deficit Quantity","Actually Transferred","Quantity Kept","Code","Distance","Quantity Per Box Mapping"])

def path(excessDFx,defiDFx,drugCode):
    global outputPath,limit,mon
    defiLoc = list(defiDFx.index)
    excessDFx.sort_values(by='quantity', inplace=True, ascending=False)
    excessLoc = list(excessDFx.index)
    for loca in excessLoc:
        loc1 = loca
        flag = True
        quant = excessDFx.loc[loc1, 'quantity']
        while quant > 0:
            if quant < limit:
                break
            temp = distanceMatrix.loc[loc1, defiLoc].copy()
            temp = pd.DataFrame(temp)
            temp.sort_values(by=loc1, inplace=True)
            if len(temp) == 0:
                break
            loc2 = temp.index[0]
            tempV = tsnDF.loc[drugCode, loc1] if flag else tsnDF.loc[drugCode, loc1]+outputPath.loc[len(outputPath.index) - 1, "Actually Transferred"]
            if quant > defiDFx.loc[loc2, 'quantity'] and defiDFx.loc[loc2,'quantity']!=0:
                if tempV>=amcDF.loc[drugCode, loc1]*mon:
                
                    outputPath.loc[len(outputPath.index)] = [loca,loc1, flag, amcDF.loc[drugCode, loc1], tempV,
                                                       tempV - amcDF.loc[drugCode, loc1] * mon, loc2,
                                                       defiDFx.loc[loc2, 'quantity'], quant,defiDFx.loc[loc2, 'quantity'], drugCode,
                                                       distanceMatrix.loc[loc1, loc2],quant/qpbmDF.loc[drugCode,'qpb']]
                    flag = False
                    quant = max(quant-defiDFx.loc[loc2, 'quantity'],0)
                    defiDFx.drop(index=loc2,axis=0,inplace=True)#loc[loc2, 'quantity'] = 0
                    defiLoc.remove(loc2)
                else:
                    break
            elif defiDFx.loc[loc2,'quantity']==0:
                defiDFx.drop(index=loc2,axis=0,inplace=True)
                defiLoc.remove(loc2)
            else:
                defiDFx.loc[loc2, 'quantity'] = max(defiDFx.loc[loc2, 'quantity']-quant,0)
                outputPath.loc[len(outputPath.index)] = [loca,loc1, flag, amcDF.loc[drugCode, loc1], tsnDF.loc[drugCode, loc1],
                                                       quant, loc2, defiDFx.loc[loc2, 'quantity'], quant, quant, drugCode,
                                                       distanceMatrix.loc[loc1, loc2],quant/qpbmDF.loc[drugCode,'qpb']]
                quant = 0
            loc1 = loc2


def excToNearDeficit(excessDFx,defiDFx,drugCode):
    global outputEx,limit,mon
    defiLoc = list(defiDFx.index)
    excessDFx.sort_values(by='quantity',inplace=True,ascending=False)
    excessLoc = list(excessDFx.index)
    for loca in excessLoc:
        temp = pd.DataFrame(distanceMatrix.loc[loca, defiLoc])
        temp.sort_values(by=loca, inplace=True)
        defiLoc = list(temp.index)
        if  excessDFx.loc[loca, 'quantity']<limit:
            continue
        while len(defiLoc) != 0 and defiDFx.loc[defiLoc[0], 'quantity'] < excessDFx.loc[loca, 'quantity']:
            outputEx.loc[len(outputEx.index)] = [loca, amcDF.loc[drugCode, loca], tsnDF.loc[drugCode, loca],
                                                   tsnDF.loc[drugCode, loca] - amcDF.loc[drugCode, loca] * mon,
                                                   excessDFx.loc[loca, 'quantity'], defiLoc[0],
                                                   defiDFx.loc[defiLoc[0], 'quantity'],
                                                   defiDFx.loc[defiLoc[0], 'quantity'], drugCode,
                                                   temp.loc[defiLoc[0], loca],defiDFx.loc[defiLoc[0], 'quantity']/qpbmDF.loc[drugCode,'qpb']]
            excessDFx.loc[loca, 'quantity'] -= defiDFx.loc[defiLoc[0], 'quantity']
            defiDFx.loc[defiLoc[0], 'quantity'] = 0
            defiLoc = defiLoc[1:]
        else:
            if len(defiLoc) == 0:
                continue
            if excessDFx.loc[loca, 'quantity'] < limit:
                continue
            outputEx.loc[len(outputEx.index)] = [loca, amcDF.loc[drugCode, loca], tsnDF.loc[drugCode, loca],
                                                       tsnDF.loc[drugCode, loca] - amcDF.loc[drugCode, loca] * mon,
                                                       excessDFx.loc[loca, 'quantity'], defiLoc[0],
                                                       defiDFx.loc[defiLoc[0], 'quantity'],
                                                       excessDFx.loc[loca, 'quantity'], drugCode,
                                                       temp.loc[defiLoc[0], loca],excessDFx.loc[loca, 'quantity']/qpbmDF.loc[drugCode,'qpb']]
            if defiDFx.loc[defiLoc[0], 'quantity'] == excessDFx.loc[loca, 'quantity']:
                excessDFx.loc[loca, 'quantity']=0
                defiDFx.loc[loca, 'quantity']=0
                defiLoc=defiLoc[1:]
            else:
                defiDFx.loc[defiLoc[0], 'quantity'] -= excessDFx.loc[loca, 'quantity']
                excessDFx.loc[loca, 'quantity'] = 0


def defFromNearExcess(excessDFx,defiDFx,drugCode):
    global outputDF,limit,mon
    defiLoc = list(defiDFx.index)
    excessLoc = list(excessDFx.index)
    for loca in defiLoc:
        temp = pd.DataFrame(distanceMatrix.loc[loca, excessLoc])
        temp.sort_values(by=loca, inplace=True,ascending=True)
        excessLoc = list(temp.index)
        while len(excessLoc) != 0 and defiDFx.loc[loca, 'quantity'] > excessDFx.loc[excessLoc[0], 'quantity']:
            if excessDFx.loc[excessLoc[0], 'quantity']<limit:
                excessLoc = excessLoc[1:]
                continue
            outputDF.loc[len(outputDF.index),:] = [excessLoc[0], amcDF.loc[drugCode, excessLoc[0]],
                                                 tsnDF.loc[drugCode, excessLoc[0]],
                                                 tsnDF.loc[drugCode, excessLoc[0]] - amcDF.loc[drugCode, excessLoc[0]] * mon,
                                                 loca, defiDFx.loc[loca, 'quantity'],
                                                 excessDFx.loc[excessLoc[0], 'quantity'], drugCode,
                                                 temp.loc[excessLoc[0], loca],excessDFx.loc[excessLoc[0], 'quantity']/qpbmDF.loc[drugCode,'qpb']]
            tsnDF.loc[drugCode, excessLoc[0]]=tsnDF.loc[drugCode, excessLoc[0]] - excessDFx.loc[excessLoc[0], 'quantity']
            defiDFx.loc[loca, 'quantity'] -= excessDFx.loc[excessLoc[0], 'quantity']
            excessDFx.loc[excessLoc[0], 'quantity'] = 0
            excessLoc = excessLoc[1:]
        else:
            if len(excessLoc) == 0:
                continue
            if excessDFx.loc[excessLoc[0], 'quantity']<limit:
                continue
            outputDF.loc[len(outputDF.index),:] = [excessLoc[0], amcDF.loc[drugCode, excessLoc[0]],
                                                     tsnDF.loc[drugCode, excessLoc[0]],
                                                     tsnDF.loc[drugCode, excessLoc[0]] - amcDF.loc[
                                                         drugCode, excessLoc[0]] * mon, loca,
                                                     defiDFx.loc[loca, 'quantity'], defiDFx.loc[loca, 'quantity'],
                                                     drugCode, temp.loc[excessLoc[0], loca],defiDFx.loc[loca, 'quantity']/qpbmDF.loc[drugCode,'qpb']]
            tsnDF.loc[drugCode, excessLoc[0]]=tsnDF.loc[drugCode, excessLoc[0]] - defiDFx.loc[loca, 'quantity']
            if defiDFx.loc[loca, 'quantity'] == excessDFx.loc[excessLoc[0], 'quantity']:
                excessDFx.loc[excessLoc[0], 'quantity']=0
                excessLoc = excessLoc[1:]
                defiDFx.loc[loca, 'quantity']=0
            else:
                excessDFx.loc[excessLoc[0], 'quantity'] -= defiDFx.loc[loca, 'quantity']
                defiDFx.loc[loca, 'quantity'] = 0


def extr(x):
    return re.findall('\[(.*)\]',x)[0]

def execute():
    global outputDF,outputEx,outputPath,choice,codes,mon,tsnDF,amcDF,wh,workbook,distanceMatrix
    distanceMatrix.index = amcDF.columns
    distanceMatrix.columns = amcDF.columns
    
    amcDF.drop(columns=wh,axis=1,inplace=True)
    tsnDF.drop(columns=wh,axis=1,inplace=True)
    distanceMatrix.drop(index=wh,axis=0,inplace=True)
    distanceMatrix.drop(columns=wh, axis=1, inplace=True)
 
    for drugCode in codes:

        mDF = tsnDF.loc[drugCode, :] / amcDF.loc[drugCode, :]
        mDF = pd.DataFrame(mDF)
        defiDF = mDF[~(mDF[drugCode]>=mon)].copy()

        indNan = defiDF[pd.isnull(defiDF[drugCode])].index
        defiDF['quantity'] = (mon - defiDF[drugCode].values) * amcDF.T.loc[defiDF.index, drugCode].values
        if len(indNan) != 0:
            defiDF.loc[indNan, 'quantity'] = tsnDF.T.loc[:, drugCode].mean()
        defiDF.drop(drugCode, axis=1, inplace=True)
        excessDF = mDF[mDF[drugCode] >mon].copy()
        excessDF['quantity'] = (excessDF[drugCode].values - mon) * amcDF.T.loc[excessDF.index, drugCode].values
        ind_ex = excessDF[excessDF[drugCode] == np.inf].index
        excessDF.loc[ind_ex, 'quantity'] = tsnDF.T.loc[ind_ex, drugCode].values
        excessDF.drop(drugCode, axis=1, inplace=True)
        defiDF=defiDF.round(0).copy()
        excessDF=excessDF.round(0).copy()
        defiDF.drop(index=defiDF[defiDF['quantity']==0].index,axis=0,inplace=True)
        if choice=='Deficit from nearest Excess':
            defFromNearExcess(excessDF.copy(),defiDF.copy(),drugCode)
        if choice=='Excess to nearest Deficit':
            excToNearDeficit(excessDF.copy(),defiDF.copy(),drugCode)
        if choice=='Path':
            path(excessDF.copy(),defiDF.copy(),drugCode)
   

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

    if not os.path.isdir("Files"):
        os.makedirs('Files')
    if choice=='Deficit from nearest Excess':
        outputDF['Date and Time'] = dt_string
        workbook = xlsxwriter.Workbook(outputDeficit,{'in_memory': True})
        worksheet = workbook.add_worksheet()
        worksheet.write_row(0, 0, outputDF.columns)
        data_format1 = workbook.add_format({'bg_color': '#FFC7CE'})

        for row in range(1, len(outputDF) + 1):
            if outputDF.loc[row - 1, 'To Warehouse'] != 'NA' and amcDF.loc[
                drugCode, outputDF.loc[row - 1, 'To Warehouse']] == 0 and tsnDF.loc[
                drugCode, outputDF.loc[row - 1, 'To Warehouse']] == 0:
                worksheet.set_row(row, cell_format=data_format1)
            worksheet.write_row(row, 0, outputDF.loc[row - 1, :])
        workbook.close()
        st.download_button(label="Download OutputDeficit File as XLSX",data=outputDeficit.getvalue(),file_name='OutputDeficit.xlsx',mime='application/vnd.ms-excel')
              
    if choice=='Excess to nearest Deficit':
        outputEx['Date and Time'] = dt_string
        workbook = xlsxwriter.Workbook(outputExcess,{'in_memory': True})
        worksheet = workbook.add_worksheet()
        worksheet.write_row(0, 0, outputEx.columns)
        data_format1 = workbook.add_format({'bg_color': '#FFC7CE'})

        for row in range(1, len(outputEx) + 1):
            if outputEx.loc[row - 1, 'To Warehouse'] != 'NA' and amcDF.loc[
                drugCode, outputEx.loc[row - 1, 'To Warehouse']] == 0 and tsnDF.loc[
                drugCode, outputEx.loc[row - 1, 'To Warehouse']] == 0:
                worksheet.set_row(row, cell_format=data_format1)
            worksheet.write_row(row, 0, outputEx.loc[row - 1, :])
        workbook.close()
        st.download_button(label="Download OutputExcess File as XLSX",data=outputExcess.getvalue(),file_name='OutputExcess.xlsx',mime='application/vnd.ms-excel')
    
    if choice=='Path':
        outputPath['Date and Time'] = dt_string
        workbook = xlsxwriter.Workbook(outputPaths,{'in_memory': True})
        worksheet = workbook.add_worksheet()
        worksheet.write_row(0, 0, outputPath.columns)
        data_format1 = workbook.add_format({'bg_color': '#FFC7CE'})

        for row in range(1, len(outputPath) + 1):
            if outputPath.loc[row - 1, 'To Warehouse'] != 'NA' and amcDF.loc[
                drugCode, outputPath.loc[row - 1, 'To Warehouse']] == 0 and tsnDF.loc[
                drugCode, outputPath.loc[row - 1, 'To Warehouse']] == 0:
                worksheet.set_row(row, cell_format=data_format1)
            worksheet.write_row(row, 0, outputPath.loc[row - 1, :])
        
        workbook.close()
        st.download_button(label="Download OutputPath File as XLSX",data=outputPaths.getvalue(),file_name='OutputPath.xlsx',mime='application/vnd.ms-excel')

def check(x):
    return True if '(E)' in x else False

def gui():
    st.set_page_config(layout="wide",initial_sidebar_state="collapsed")
    hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div.block-container{padding-top:0rem;}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    st.title('Inter Warehouse Transfer Tool')
    st.sidebar.write("""Files Uploaded""")
    global qpbmDF,amcDF,tsnDF, codes, wh, distanceMatrix, allWarehouse,choice,limit,mon

    amcFile = st.file_uploader('Upload AMC(Average monthly consumption) File', type=['csv'], key=1)  # bytes
    if amcFile is not None:
        st.sidebar.subheader('AMC File ✅')
        amcDF = pd.read_csv(amcFile,encoding='latin-1')
        amc_col = list(amcDF.columns)
        for ind in range(len(amc_col)):
            amc_col[ind] = amc_col[ind].replace(' ', '')
            amc_col[ind] = amc_col[ind].replace('DrugWarehouse(UPMSCL)', '')
            amc_col[ind] = amc_col[ind].replace('Warehouse(UPMSCL)', '')
        amcDF.columns = amc_col
        amcDF['temp']=amcDF['drugname'].apply(check)
        amcDF=amcDF[amcDF['temp']].copy()
        amcDF.reset_index(drop=True,inplace=True)
        amcDF['DrugCode'] = amcDF['drugname'].apply(extr)
        amcDF.drop(columns=['drugname','temp'], axis=1, inplace=True)
        amcDF.set_index('DrugCode', inplace=True)
        amcDF=amcDF.div(12).round(0).copy()

    tsn = st.file_uploader('Upload TS(Total stock) File', type=['csv'], key=2)  # bytes
    if tsn is not None:
        st.sidebar.subheader('TS File ✅')
        tsnDF = pd.read_csv(tsn,encoding='latin-1')
        tsn_col = list(tsnDF.columns)
        for ind in range(len(tsn_col)):
            tsn_col[ind] = tsn_col[ind].replace(' ', '')
            tsn_col[ind] = tsn_col[ind].replace('DrugWarehouse(UPMSCL)', '')
            tsn_col[ind] = tsn_col[ind].replace('Warehouse(UPMSCL)', '')
        tsnDF.columns = tsn_col
        tsnDF['temp']=tsnDF['DrugName'].apply(check)
        tsnDF=tsnDF[tsnDF['temp']].copy()
        tsnDF.reset_index(drop=True,inplace=True)
        tsnDF['DrugCode'] = tsnDF['DrugName'].apply(extr)
        tsnDF.drop(columns=['DrugName','temp'], axis=1, inplace=True)
        tsnDF.set_index('DrugCode', inplace=True)
        tsnCodes = list(tsnDF.index)
        amcCodes = list(amcDF.index)
        commonCodes = list(set(tsnCodes).intersection(amcCodes))
        tsnNotCommonCodes = list(set(tsnCodes).difference(set(commonCodes)))
        amcNotCommonCodes = list(set(amcCodes).difference(set(commonCodes)))
        amcDF.drop(index=amcNotCommonCodes, axis=0, inplace=True)
        tsnDF.drop(index=tsnNotCommonCodes, axis=0, inplace=True)
        codeList = list(tsnDF.index)
        codeList.sort()
        codes = st.multiselect('Select DrugCodes', codeList, codeList, key='m1')
        whList = list(amcDF.columns)
        wh0 = st.multiselect('Select Warehouses', whList, whList)
        wh = list(set(whList).difference(set(wh0)))

    limit=st.text_input('Enter the minimum value a warehouse should transfer (>=0)')
    if limit!='':
        limit=int(limit)
        
    agreeMon = st.checkbox('Change the number of months for which stock is to be considered',key='cb6')
    if agreeMon:
        mon = st.text_input('Enter the number of months for which stock is to be considered')
        if mon != '':
            mon = int(mon)

    agree = st.checkbox('Change GeoLocations',key='cb1')
    def separate(x):
        x = x.replace(" ", "")
        temp = x.split(',')
        return (float(temp[0]), float(temp[1]))

    allWhDF=pd.DataFrame()
    if agree and allWhDF.empty:
        allWarehouse = st.file_uploader('Upload All warehouse locations File(map coordinates for each warehouse location)', type=['csv'], key=5)
        if allWarehouse is not None:
            allWhDF = pd.read_csv(allWarehouse)
    else:
        st.sidebar.subheader('All Warehouses Location File ✅')
        allWhDF = pd.read_csv('Geo Coordinates.csv')


    if not allWhDF.empty:
        allWhDF['Coordinates'] = allWhDF['Map Coordinates'].apply(separate)
        allWhDF.drop(columns=['Sr.No.', 'Map Coordinates'], axis=1, inplace=True)
        allWhDF.set_index('Warehouse', inplace=True)
        distanceMatrix = pd.DataFrame(columns=list(allWhDF.index), index=list(allWhDF.index))
        for wh1 in list(allWhDF.index):
            for wh2 in list(allWhDF.index):
                distanceMatrix.loc[wh1, wh2] = geodesic(allWhDF.loc[wh1, 'Coordinates'], allWhDF.loc[wh2, 'Coordinates']).km

    agreeQPB = st.checkbox('Change Quantity Per Box Mapping',key='cb2')
    if agreeQPB and qpbmDF.empty:
        qpbmFile = st.file_uploader('Upload QPB File(quantity per box)', type=['csv'], key=6)  # bytes
        if qpbmFile is not None:
            qpbmDF = pd.read_csv(qpbmFile)
            qpbmDF.set_index('DrugCode', inplace=True)
    else:
        st.sidebar.subheader('QPBM File ✅')
        qpbmDF = pd.read_csv('qpb.csv')
        qpbmDF.set_index('DrugCode', inplace=True)

    choice = st.radio("Select Module",('Deficit from nearest Excess', 'Excess to nearest Deficit', 'Path'))

    if limit!='' and not amcDF.empty and not tsnDF.empty and not distanceMatrix.empty and not qpbmDF.empty and choice and mon!='':
        buttonClick=st.button("Run")
        if buttonClick:
            execute()

gui()
