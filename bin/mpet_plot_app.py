from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import os
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import argparse
from argparse import RawTextHelpFormatter

import mpet.geometry as geom
from mpet import mod_cell
from mpet import utils
from mpet.config import Config, constants

#  from plotly.subplots import make_subplots
#  import plotly.graph_objects as go
desc = """ Dashboard that shows all plots and compares the resutls of different models."""
parser = argparse.ArgumentParser(description=desc, formatter_class=RawTextHelpFormatter)
parser.add_argument('-d', '--dataDir',
                    help='Directory that contains folders with simulation output')
args = parser.parse_args()

app = Dash(__name__)

# Define colors to be used
colors = {
    'background': '#FFFFFF',
    'text': '#000000',
    'bg_table': '#B9B6B6',
    'text_table': '#111111',
}

# Import data from all folders in sim_output into one dataframe
# Read in the simulation results and calcuations data
dataFiles = [os.path.join(args.dataDir, f) for f in os.listdir(args.dataDir)
             if os.path.isdir(os.path.join(args.dataDir, f))]
dff = pd.DataFrame()
dff_c_sub = pd.DataFrame()
dff_cd_sub = pd.DataFrame()
dff_csld_sub = pd.DataFrame()

for indir in dataFiles:
    pfx = 'mpet.'
    sStr = "_"
    ttl_fmt = "% = {perc:2.1f}"
    # Read in the simulation results and calcuations data
    model = os.path.basename(indir)
    dataFileName = "output_data"
    dataFile = os.path.join(indir, dataFileName)
    data = utils.open_data_file(dataFile)
    try:
        utils.get_dict_key(data, pfx + 'current')
    except KeyError:
        pfx = ''
    try:
        utils.get_dict_key(data, pfx + "partTrodecvol0part0" + sStr + "cbar")
    except KeyError:
        sStr = "."
    # Read in the parameters used to define the simulation
    config = Config.from_dicts(indir)
    # simulated (porous) electrodes
    trodes = config["trodes"]
    # Pick out some useful calculated values
    limtrode = config["limtrode"]
    k = constants.k                      # Boltzmann constant, J/(K Li)
    Tref = constants.T_ref               # Temp, K
    e = constants.e                      # Charge of proton, C
    F = constants.F                      # C/mol
    c_ref = constants.c_ref
    td = config["t_ref"]
    Etheta = {"a": 0.}
    cap = config[limtrode, "cap"]
    for trode in trodes:
        Etheta[trode] = -(k*Tref/e) * config[trode, "phiRef"]
    Vstd = Etheta["c"] - Etheta["a"]
    dataReporter = config["dataReporter"]
    Nvol = config["Nvol"]
    Npart = config["Npart"]
    psd_len = config["psd_len"]
    # Discretization (and associated porosity)
    Lfac = 1e6
    Lunit = r"$\mu$m"
    dxc = config["L"]["c"]/Nvol["c"]
    dxvec = np.array(Nvol["c"] * [dxc])
    porosvec = np.array(Nvol["c"] * [config["poros"]["c"]])
    cellsvec = dxc*np.arange(Nvol["c"]) + dxc/2.
    if config["have_separator"]:
        dxs = config["L"]["s"]/Nvol["s"]
        dxvec_s = np.array(Nvol["s"] * [dxs])
        dxvec = np.hstack((dxvec_s, dxvec))
        poros_s = np.array(Nvol["s"] * [config["poros"]["s"]])
        porosvec = np.hstack((poros_s, porosvec))
        cellsvec += config["L"]["s"] / config["L"]["c"]
        cellsvec_s = dxs*np.arange(Nvol["s"]) + dxs/2.
        cellsvec = np.hstack((cellsvec_s, cellsvec))
    if "a" in trodes:
        dxa = config["L"]["a"]/Nvol["a"]
        dxvec_a = np.array(Nvol["a"] * [dxa])
        dxvec = np.hstack((dxvec_a, dxvec))
        poros_a = np.array(Nvol["a"] * [config["poros"]["a"]])
        porosvec = np.hstack((poros_a, porosvec))
        cellsvec += config["L"]["a"] / config["L"]["c"]
        cellsvec_a = dxa*np.arange(Nvol["a"]) + dxa/2.
        cellsvec = np.hstack((cellsvec_a, cellsvec))
    cellsvec *= config["L_ref"] * Lfac
    facesvec = np.insert(np.cumsum(dxvec), 0, 0.) * config["L_ref"] * Lfac
    # Extract the reported simulation times
    times = utils.get_dict_key(data, pfx + 'phi_applied_times')
    numtimes = len(times)
    tmin = np.min(times)
    tmax = np.max(times)
    # Voltage profile
    timestd = times*td
    voltage = (Vstd - (k*Tref/e)*utils.get_dict_key(data, pfx + 'phi_applied'))
    # surface concentration
    # soc profile
    ffvec_c = utils.get_dict_key(data, pfx + 'ffrac_c')
    try:
        ffvec_a = utils.get_dict_key(data, pfx + 'ffrac_a')
        nparta = Npart["a"]
        nvola = Nvol["a"]
    except KeyError:
        ffvec_a = 0
        nparta = 0
        nvola = 0
    # Elytecons
    # current
    theoretical_1C_current = config[config['limtrode'], "cap"] / 3600.  # A/m^2
    current = (utils.get_dict_key(data, pfx + 'current')
               * theoretical_1C_current / config['1C_current_density'] * config['curr_ref'])
    # Power
    current_p = utils.get_dict_key(data, pfx + 'current') * (3600/td) * (cap/3600)  # in A/m^2
    voltage_p = (Vstd - (k*Tref/e)*utils.get_dict_key(data, pfx + 'phi_applied'))  # in V
    power = np.multiply(current_p, voltage_p)

    # Electrolyte concetration / potential
    datax = cellsvec
    c_sep, p_sep = pfx + 'c_lyte_s', pfx + 'phi_lyte_s'
    c_anode, p_anode = pfx + 'c_lyte_a', pfx + 'phi_lyte_a'
    c_cath, p_cath = pfx + 'c_lyte_c', pfx + 'phi_lyte_c'
    datay_c = utils.get_dict_key(data, c_cath, squeeze=False)
    datay_p = utils.get_dict_key(data, p_cath, squeeze=False)
    L_c = config['L']["c"] * config['L_ref'] * Lfac
    Ltot = L_c
    if config["have_separator"]:
        datay_s_c = utils.get_dict_key(data, c_sep, squeeze=False)
        datay_s_p = utils.get_dict_key(data, p_sep, squeeze=False)
        datay_c = np.hstack((datay_s_c, datay_c))
        datay_p = np.hstack((datay_s_p, datay_p))
        L_s = config['L']["s"] * config['L_ref'] * Lfac
        Ltot += L_s
    else:
        L_s = 0
    if "a" in trodes:
        datay_a_c = utils.get_dict_key(data, c_anode, squeeze=False)
        datay_a_p = utils.get_dict_key(data, p_anode, squeeze=False)
        datay_c = np.hstack((datay_a_c, datay_c))
        datay_p = np.hstack((datay_a_p, datay_p))
        L_a = config['L']["a"] * config['L_ref'] * Lfac
        Ltot += L_a
    else:
        L_a = 0
    xmin = 0
    xmax = Ltot
    # elytec
    ylbl_ce = 'Concentration of electrolyte [M]'
    datay_ce = datay_c * c_ref / 1000.
    # elytep
    ylbl_pe = 'Potential of electrolyte [V]'
    datay_pe = datay_p*(k*Tref/e) - Vstd
    cGP_L = utils.get_dict_key(data, "c_lyteGP_L")
    pGP_L = utils.get_dict_key(data, "phi_lyteGP_L")
    cmat = np.hstack((cGP_L.reshape((-1,1)), datay_c, datay_c[:,-1].reshape((-1,1))))
    pmat = np.hstack((pGP_L.reshape((-1,1)), datay_p, datay_p[:,-1].reshape((-1,1))))
    disc = geom.get_elyte_disc(Nvol, config["L"], config["poros"], config["BruggExp"])
    i_edges = np.zeros((numtimes, len(facesvec)))
    for tInd in range(numtimes):
        i_edges[tInd, :] = mod_cell.get_lyte_internal_fluxes(
            cmat[tInd, :], pmat[tInd, :], disc, config)[1]
    # elytei
    ylbl_cd = r'Current density of electrolyte [A/m$^2$]'
    datax_cd = facesvec
    datay_cd = i_edges * (F*constants.c_ref*config["D_ref"]/config["L_ref"])
    # elytedivi
    ylbl_d = r'Divergence of electrolyte current density [A/m$^3$]'
    datax_d = cellsvec
    datay_d = np.diff(i_edges, axis=1) / disc["dxvec"]
    datay_d *= (F*constants.c_ref*config["D_ref"]/config["L_ref"]**2)
    # fraction
    t_current = times
    tfrac = (t_current - tmin)/(tmax - tmin) * 100
    # elytecons
    sep = pfx + 'c_lyte_s'
    anode = pfx + 'c_lyte_a'
    cath = pfx + 'c_lyte_c'
    cvec = utils.get_dict_key(data, cath)
    if config["have_separator"]:
        cvec_s = utils.get_dict_key(data, sep)
        cvec = np.hstack((cvec_s, cvec))
    if "a" in trodes:
        cvec_a = utils.get_dict_key(data, anode)
        cvec = np.hstack((cvec_a, cvec))
    cavg = np.sum(porosvec*dxvec*cvec, axis=1)/np.sum(porosvec*dxvec)

    df = pd.DataFrame({
        "Model": model,
        "Config trode type": config[trode, "type"],
        "Voltage (V)": voltage,
        "Cathode Filling Fraction": ffvec_c,
        "Anode Filling Fraction": ffvec_a,
        "Time (s)": timestd,
        "Npartc": Npart["c"],
        "Nvolc": Nvol["c"],
        "Nparta": nparta,
        "Nvola": nvola,
        "Current": current,
        "Power": power,
        "cavg": cavg
    })

    for trode in trodes:
        partStr = "partTrode{trode}vol{{vInd}}part{{pInd}}".format(trode=trode) + sStr
        str_base = (pfx + partStr + "c")
        for pInd in range(Npart[trode]):
            for vInd in range(Nvol[trode]):
                sol_str = str_base.format(pInd=pInd, vInd=vInd)
                sol_str_data = utils.get_dict_key(data, sol_str, squeeze=False)[:,-1]
                df[sol_str] = sol_str_data
                # for cbar data
                if config[trode, "type"] in constants.one_var_types:
                    str_cbar_base = pfx + partStr + "cbar"
                    sol_cbar_str = str_cbar_base.format(pInd=pInd, vInd=vInd)
                    sol_cbar_str_data = utils.get_dict_key(data, sol_cbar_str)
                    df[sol_cbar_str] = sol_cbar_str_data
                elif config[trode, "type"] in constants.two_var_types:
                    str1_cbar_base = pfx + partStr + "c1bar"
                    str2_cbar_base = pfx + partStr + "c2bar"
                    sol1_cbar_str = str1_cbar_base.format(pInd=pInd, vInd=vInd)
                    sol2_cbar_str = str2_cbar_base.format(pInd=pInd, vInd=vInd)
                    sol1_cbar_str_data = utils.get_dict_key(data, sol1_cbar_str)
                    sol2_cbar_str_data = utils.get_dict_key(data, sol2_cbar_str)
                    df[sol1_cbar_str] = sol1_cbar_str_data
                    df[sol2_cbar_str] = sol2_cbar_str_data

    dff = pd.concat([dff, df], ignore_index=True)

    # build dataframe for plots electrolyte concentration or potential
    # and for csld subplot animation (time, pind, vind, y)
    dff_c = pd.DataFrame()
    dff_cd = pd.DataFrame()
    dff_csld = pd.DataFrame()
    for i in range(len(datay_ce)):
        df_c = pd.DataFrame({"Model": model,
                             "fraction": round(tfrac[i]),
                             "fraction orig": tfrac[i],
                             "cellsvec": cellsvec[:],
                             "Concentration electrolyte": datay_ce[i,:],
                             "Potential electrolyte": datay_pe[i,:],
                             "Divergence electrolyte curr dens": datay_d[i,:]
                             })
        dff_c = pd.concat([dff_c, df_c], ignore_index=True)
    for i in range(len(datay_cd)):
        df_cd = pd.DataFrame({"Model": model,
                              "fraction": round(tfrac[i]),
                              "fraction orig": tfrac[i],
                              "facesvec": facesvec[:],
                              "Curreny density electrolyte": datay_cd[i,:]
                              })
        dff_cd = pd.concat([dff_cd, df_cd], ignore_index=True)
    for t in range(len(timestd)):
        for trode in trodes:
            partStr = "partTrode{trode}vol{{vInd}}part{{pInd}}".format(trode=trode) + sStr
            for pInd in range(Npart[trode]):
                for vInd in range(Nvol[trode]):
                    lens_str = "lens_{vInd}_{pInd}".format(vInd=vInd, pInd=pInd)
                    if config[trode, "type"] in constants.one_var_types:
                        cstr_base = pfx + partStr + "c"
                        cstr = cstr_base.format(trode=trode, pInd=pInd, vInd=vInd)
                        datay = utils.get_dict_key(data, cstr)[t]
                        datax = np.linspace(0, psd_len[trode][vInd,pInd] * Lfac, len(datay))
                        if trode == trodes[0] and pInd == 0 and vInd == 0:
                            df_csld = pd.DataFrame({"Model": model,
                                                    "time (s)": timestd[t],
                                                    "time fraction": round(tfrac[t]),
                                                    "fraction orig": tfrac[t],
                                                    lens_str: datax,
                                                    cstr: datay
                                                    })
                        else:
                            df_csld[lens_str] = pd.Series(datax)
                            df_csld[cstr] = pd.Series(datay)
                    elif config[trode, "type"] in constants.two_var_types:
                        c1str_base = pfx + partStr + "c1"
                        c2str_base = pfx + partStr + "c2"
                        c3str_base = pfx + partStr + "cav"
                        c1str = c1str_base.format(trode=trode, pInd=pInd, vInd=vInd)
                        c2str = c2str_base.format(trode=trode, pInd=pInd, vInd=vInd)
                        c3str = c3str_base.format(trode=trode, pInd=pInd, vInd=vInd)
                        datay1 = utils.get_dict_key(data, c1str[pInd,vInd])[t]
                        datay2 = utils.get_dict_key(data, c2str[pInd,vInd])[t]
                        datay3 = 0.5*(datay1 + datay2)
                        numy = len(datay1) if isinstance(datay1, np.ndarray) else 1
                        datax = np.linspace(0, psd_len[trode][vInd,pInd] * Lfac, numy)
                        if pInd == 0 and vInd == 0:
                            df_csld = pd.DataFrame({"Model": model,
                                                    "time (s)": timestd[t],
                                                    "time fraction": round(tfrac[i]),
                                                    "fraction orig": tfrac[i],
                                                    lens_str: datax,
                                                    c1str: datay1,
                                                    c2str: datay2,
                                                    c3str: datay3
                                                    })
                        else:
                            df_csld[lens_str] = pd.Series(datax)
                            df_csld[c1str] = pd.Series(datay1)
                            df_csld[c2str] = pd.Series(datay2)
                            df_csld[c3str] = pd.Series(datay3)
        dff_csld = pd.concat([dff_csld, df_csld], ignore_index=True)
    # make subselection dataframe with one fraction per rounded fraction
    for i in np.unique(dff_c["fraction"]):
        df_sub = dff_c[dff_c["fraction"] == i]
        md = 1.0
        mdx = 0.0
        for j in np.unique(df_sub["fraction orig"]):
            dx = abs(i-j)
            if dx < md:
                md = dx
                mdx = j
        select = dff_c[dff_c["fraction orig"] == mdx]
        dff_c_sub = pd.concat([dff_c_sub, select], ignore_index=True)
    for i in np.unique(dff_cd["fraction"]):
        df_cd_sub = dff_cd[dff_cd["fraction"] == i]
        md = 1.0
        mdx = 0.0
        for j in np.unique(df_cd_sub["fraction orig"]):
            dx = abs(i-j)
            if dx < md:
                md = dx
                mdx = j
        select = dff_cd[dff_cd["fraction orig"] == mdx]
        dff_cd_sub = pd.concat([dff_cd_sub, select], ignore_index=True)
    for i in np.unique(dff_csld["time fraction"]):
        df_csld_sub = dff_csld[dff_csld["time fraction"] == i]
        md = 1.0
        mdx = 0.0
        for j in np.unique(df_csld_sub["fraction orig"]):
            dx = abs(i-j)
            if dx < md:
                md = dx
                mdx = j
        select = dff_csld[dff_csld["fraction orig"] == mdx]
        dff_csld_sub = pd.concat([dff_csld_sub, select], ignore_index=True)
############################
# Define plots
############################

# Define Markdown text
markdown_text = '''
# MPET visualisation

This dashboard shows visualisations of all the MPET simulation output saved in the folder
''' + args.dataDir

defaultmodel = (dff['Model'].unique()[0])
# Define components of app
app.layout = html.Div(style={'backgroundColor': colors['background']},
                      children=[
                      html.Div(style={'backgroundColor': 'DodgerBlue'},
                               children=[
                               dcc.Markdown(
                                   children=markdown_text,
                                   style={'textAlign': 'center',
                                          'color': colors['text'],
                                          'font-family':'Sans-serif'}),
                                   html.H4(children='Select models to display in all plots:',
                                           style={'font-family':'Sans-serif'}),
                                   dcc.Checklist(options=dff['Model'].unique(),
                                                 value=dff['Model'].unique(),
                                                 id='model-selection',
                                                 labelStyle={'display': 'block'},
                                                 style={'font-family':'Sans-serif',
                                                        'margin-bottom': '20px',
                                                        'background': 'DodgerBlue'}),
                                   html.Hr(style={"color": 'black', 'borderWidth': '10'})]),
                      # v/vt
                      html.H3(children='Voltage',
                              style={'textAlign': 'center', 'font-family':'Sans-serif'}),
                      dcc.Dropdown(['Time (s)', 'Cathode Filling Fraction'], 'Time (s)',
                                   id='xaxis-column',
                                   style={'width':'50%', 'font-family':'Sans-serif'}),
                      dcc.Graph(id='Voltage-graph-double'),
                      html.Hr(style={"color": 'black'}),
                      html.Hr(style={"color": 'black'}),
                      # curr
                      html.H3(children='Current profile',
                              style={'textAlign': 'center', 'font-family':'Sans-serif'}),
                      dcc.Graph(id="current"),
                      html.Hr(style={"color": 'black'}),
                      html.Hr(style={"color": 'black'}),
                      # power
                      html.H3(children='Power',
                              style={'textAlign': 'center', 'font-family':'Sans-serif'}),
                      dcc.Graph(id="power"),
                      html.Hr(style={"color": 'black'}),
                      html.Hr(style={"color": 'black'}),
                      # elytec
                      html.H3(children='Electrolyte concentration',
                              style={'textAlign': 'center', 'font-family':'Sans-serif'}),
                      dcc.Graph(id='electrolyte-concentration-ani'),
                      html.Hr(style={"color": 'black'}),
                      html.Hr(style={"color": 'black'}),
                      # elytep
                      html.H3(children='Electrolyte potential',
                              style={'textAlign': 'center', 'font-family':'Sans-serif'}),
                      dcc.Graph(id='electrolyte-potential-ani'),
                      html.Hr(style={"color": 'black'}),
                      html.Hr(style={"color": 'black'}),
                      # elytei
                      html.H3(children='Electrolyte current density',
                              style={'textAlign': 'center', 'font-family':'Sans-serif'}),
                      dcc.Graph(id='electrolyte-cd-ani'),
                      html.Hr(style={"color": 'black'}),
                      html.Hr(style={"color": 'black'}),
                      # elytedivi
                      html.H3(children='Divergence of electrolyte current density',
                              style={'textAlign': 'center', 'font-family':'Sans-serif'}),
                      dcc.Graph(id='electrolyte-decd-ani'),
                      html.Hr(style={"color": 'black'}),
                      html.Hr(style={"color": 'black'}),
                      # surfc/surfa
                      html.H3(children='Solid surface concentration',
                              style={'textAlign': 'center', 'font-family':'Sans-serif'}),
                      dcc.Dropdown(options=dff['Model'].unique(), value=defaultmodel,
                                   id='select_surf_model',
                                   style={'width':'50%', 'font-family':'Sans-serif'}),
                      dcc.Graph(id='Surface-concentration-anode'),
                      dcc.Graph(id='Surface-concentration-cathode'),
                      html.Hr(style={"color": 'black'}),
                      html.Hr(style={"color": 'black'}),
                      # soc_c/soc_a
                      html.H3(children='Overall utilization / state of charge of electrode',
                              style={'textAlign': 'center', 'font-family':'Sans-serif'}),
                      dcc.Graph(id='Cathode-filling-fraction'),
                      dcc.Graph(id='Anode-filling-fraction'),

                      html.Hr(style={"color": 'black'}),
                      html.Hr(style={"color": 'black'}),
                      # elytecons
                      html.H3(children='Average concentration of electrolyte',
                              style={'textAlign': 'center', 'font-family':'Sans-serif'}),
                      dcc.Graph(id='elytecons'),
                      html.Hr(style={"color": 'black'}),
                      html.Hr(style={"color": 'black'}),
                      # csld
                      html.H3(children='All solid concentrations',
                              style={'textAlign': 'center', 'font-family':'Sans-serif'}),
                      dcc.Dropdown(options=dff['Model'].unique(), value=defaultmodel,
                                   id='select_csld_model',
                                   style={'width':'50%', 'font-family':'Sans-serif'}),
                      html.H4(children='Time percentage',
                              style={'textAlign': 'left', 'font-family':'Sans-serif'}),
                      dcc.Slider(0,100,step=1,value=0,
                                 id='timefraction_slider',
                                 marks={
                                    0: '0', 5: '5', 10: '10', 15: '15', 20: '20',
                                    25: '25', 30: '30', 35: '35', 40: '40', 45: '45',
                                    50: '50', 55: '55', 60: '60', 65: '65', 70: '70',
                                    75: '75', 80: '80', 85: '85', 90: '90', 95: '95',
                                    100: '100'
                                 }, tooltip={"placement": "top", "always_visible": True}),
                      dcc.Graph(id='csld_c'),
                      dcc.Graph(id='csld_a'),
                      html.Hr(style={"color": 'black'}),
                      html.Hr(style={"color": 'black'}),
                      # cbarline
                      html.H3(children='Average concentration in each particle of electrode',
                              style={'textAlign': 'center', 'font-family':'Sans-serif'}),
                      dcc.Dropdown(options=dff['Model'].unique(), value=defaultmodel,
                                   id='select_cbarline_model',
                                   style={'width':'50%', 'font-family':'Sans-serif'}),
                      dcc.Graph(id='cbarline_c'),
                      dcc.Graph(id='cbarline_a'),

                      html.Hr(style={"color": 'black'}),
                      html.Hr(style={"color": 'black'}),
                      # 
                      html.H3(children='Average solid concentrations',
                              style={'textAlign': 'center', 'font-family':'Sans-serif'}),

                      html.Hr(style={"color": 'black'}),
                      html.Hr(style={"color": 'black'}),

                      html.H3(children='Cathode potential',
                              style={'textAlign': 'center', 'font-family':'Sans-serif'}),

                      html.Hr(style={"color": 'black'}),
                      html.Hr(style={"color": 'black'})
                      ])


# Do alllll the callbacks
@app.callback(
    Output('Voltage-graph-double', 'figure'),
    Input('xaxis-column', 'value'),
    Input('model-selection', 'value')
    )
def update_graph(xaxis_column_name, model_selection
                 ):
    fig = px.line(x=dff[xaxis_column_name][np.in1d(dff['Model'], model_selection)],
                  y=dff['Voltage (V)'][np.in1d(dff['Model'], model_selection)],
                  color=dff["Model"][np.in1d(dff['Model'], model_selection)])
    fig.update_layout(margin={'l': 40, 'b': 80, 't': 10, 'r': 0}, hovermode='closest')
    fig.update_yaxes(title='Voltage (V)',
                     type='linear')
    fig.update_xaxes(title=xaxis_column_name,
                     type='linear'
                     )
    return fig


@app.callback(
    Output('Surface-concentration-anode', 'figure'),
    Input('select_surf_model', 'value')
    )
def update_graph_surfa(select_model):
    try:
        str_base = (pfx
                    + "partTrode{trode}vol{{vInd}}part{{pInd}}".format(trode='a')
                    + sStr + "c")
        r = int(max(dff["Nparta"][dff['Model'] == select_model]))
        c = int(max(dff["Nvola"][dff['Model'] == select_model]))
        fig = make_subplots(rows=r, cols=c, shared_xaxes=True, shared_yaxes=True,
                            x_title='Time [s]', y_title='Solid surface concentration',
                            row_titles=['Particle ' + str(n) for n in range(1, r+1)],
                            column_titles=['Volume ' + str(n) for n in range(1, c+1)])
        for rr in range(0, r):
            for cc in range(0, c):
                sol_str = str_base.format(pInd=rr, vInd=cc)
                datax = dff['Time (s)'][dff['Model'] == select_model]
                datay = dff[sol_str][dff['Model'] == select_model]
                fig.add_trace(
                    trace=go.Scatter(x=datax, y=datay, line_color='darkslategray'),
                    row=rr+1, col=cc+1)
        fig.update_yaxes(range=[0,1.01])
        fig.update_layout(height=((r+1)*150), showlegend=False, title='Anode')
    except ValueError:
        fig = px.line(title='Selected model has no anode')
    return fig


@app.callback(
    Output('Surface-concentration-cathode', 'figure'),
    Input('select_surf_model', 'value')
    )
def update_graph_surfc(select_model):
    str_base = (pfx
                + "partTrode{trode}vol{{vInd}}part{{pInd}}".format(trode='c')
                + sStr + "c")
    r = int(max(dff["Npartc"][dff['Model'] == select_model]))
    c = int(max(dff["Nvolc"][dff['Model'] == select_model]))
    fig = make_subplots(rows=r, cols=c, shared_xaxes=True, shared_yaxes=True,
                        x_title='Time (s)', y_title='Solid surface concentration',
                        row_titles=['Particle ' + str(n) for n in range(1, r+1)],
                        column_titles=['Volume ' + str(n) for n in range(1, c+1)])
    for rr in range(0, r):
        for cc in range(0, c):
            sol_str = str_base.format(pInd=rr, vInd=cc)
            datax = dff['Time (s)'][dff['Model'] == select_model]
            datay = dff[sol_str][dff['Model'] == select_model]
            fig.add_trace(
                trace=go.Scatter(x=datax, y=datay, line_color='darkslategray'),
                row=rr+1, col=cc+1)
    fig.update_yaxes(range=[0,1.01])
    fig.update_layout(height=((r+1)*150), showlegend=False, title='Cathode')
    return fig


@app.callback(
    Output('Cathode-filling-fraction', 'figure'),
    Input('model-selection', 'value')
    )
def update_graph2(model_selection):
    fig = px.line(x=dff['Time (s)'][np.in1d(dff['Model'], model_selection)],
                  y=dff['Cathode Filling Fraction'][np.in1d(dff['Model'], model_selection)],
                  color=dff["Model"][np.in1d(dff['Model'], model_selection)])
    fig.update_yaxes(range=[0,1], title='Cathode Filling Fraction')
    fig.update_xaxes(title='Time [s]')

    fig.update_layout(margin={'l': 40, 'b': 80, 't': 10, 'r': 0}, hovermode='closest')

    return fig


@app.callback(
    Output('Anode-filling-fraction', 'figure'),
    Input('model-selection', 'value')
    )
def update_graph3(model_selection):

    fig = px.line(x=dff['Time (s)'][np.in1d(dff['Model'], model_selection)],
                  y=dff['Anode Filling Fraction'][np.in1d(dff['Model'], model_selection)],
                  color=dff["Model"][np.in1d(dff['Model'], model_selection)])
    fig.update_yaxes(range=[0,1], title='Anode Filling Fraction')
    fig.update_xaxes(title='Time [s]')
    fig.update_layout(margin={'l': 40, 'b': 80, 't': 10, 'r': 0}, hovermode='closest')
    return fig


@app.callback(
    Output('elytecons', 'figure'),
    Input('model-selection', 'value')
    )
def update_graph32(model_selection):
    fig = px.line(x=dff['Time (s)'][np.in1d(dff['Model'], model_selection)],
                  y=dff['cavg'][np.in1d(dff['Model'], model_selection)],
                  color=dff["Model"][np.in1d(dff['Model'], model_selection)])
    fig.update_yaxes(title='Avg. Concentration of electrolyte [nondim]')
    fig.update_xaxes(title='Time [s]')
    fig.update_layout(margin={'l': 40, 'b': 80, 't': 10, 'r': 0}, hovermode='closest')
    return fig


@app.callback(
    Output('current', 'figure'),
    Input('model-selection', 'value')
    )
def update_graph4(model_selection):
    fig = px.line(x=dff['Time (s)'][np.in1d(dff['Model'], model_selection)],
                  y=dff['Current'][np.in1d(dff['Model'], model_selection)],
                  color=dff["Model"][np.in1d(dff['Model'], model_selection)])
    fig.update_yaxes(title='Current [C-rate]')
    fig.update_xaxes(title='Time [s]')
    fig.update_layout(margin={'l': 40, 'b': 80, 't': 10, 'r': 0}, hovermode='closest')
    return fig


@app.callback(
    Output('power', 'figure'),
    Input('model-selection', 'value')
    )
def update_graph5(model_selection):
    fig = px.line(x=dff['Time (s)'][np.in1d(dff['Model'], model_selection)],
                  y=dff['Power'][np.in1d(dff['Model'], model_selection)],
                  color=dff["Model"][np.in1d(dff['Model'], model_selection)])
    fig.update_yaxes(title=u'Power [W/m\u00b2]')
    fig.update_xaxes(title='Time [s]')
    fig.update_layout(margin={'l': 40, 'b': 80, 't': 10, 'r': 0}, hovermode='closest')
    return fig


@app.callback(
    Output('electrolyte-concentration-ani', 'figure'),
    Input('model-selection', 'value'))
def display_animated_graph(model_selection):
    m_select = dff_c_sub[np.in1d(dff_c_sub['Model'], model_selection)]
    max_y = max(m_select["Concentration electrolyte"])
    min_y = min(m_select["Concentration electrolyte"])
    fig = px.line(dff_c_sub[np.in1d(dff_c_sub['Model'], model_selection)],
                  x="cellsvec",
                  y="Concentration electrolyte",
                  color="Model",
                  animation_frame="fraction")
    fig.update_yaxes(title='Concentration of electrolyte [M]',
                     range=[0.9*min_y, 1.1*max_y])
    fig.update_xaxes(title=' Battery Position [microm] ')
    fig.update_layout(margin={'l': 40, 'b': 80, 't': 10, 'r': 0}, hovermode='closest')
    fig.update_layout(transition_duration=500)

    return fig


@app.callback(
    Output('electrolyte-potential-ani', 'figure'),
    Input('model-selection', 'value'))
def display_animated_graph_pot(model_selection):
    m_select = dff_c_sub[np.in1d(dff_c_sub['Model'], model_selection)]
    max_y = max(m_select["Potential electrolyte"])
    min_y = min(m_select["Potential electrolyte"])
    fig = px.line(dff_c_sub[np.in1d(dff_c_sub['Model'], model_selection)],
                  x="cellsvec",
                  y="Potential electrolyte",
                  color="Model",
                  animation_frame="fraction")
    fig.update_yaxes(title='Potential of electrolyte [V]',
                     range=[1.1*min_y, 0.9*max_y])
    fig.update_xaxes(title=' Battery Position [microm] ')
    fig.update_layout(margin={'l': 40, 'b': 80, 't': 10, 'r': 0}, hovermode='closest')
    fig.update_layout(transition_duration=500)
    return fig


@app.callback(
    Output('electrolyte-cd-ani', 'figure'),
    Input('model-selection', 'value'))
def display_animated_graph_cd(model_selection):
    m_select = dff_cd_sub[np.in1d(dff_cd_sub['Model'], model_selection)]
    max_y = max(m_select["Curreny density electrolyte"])
    min_y = min(m_select["Curreny density electrolyte"])
    fig = px.line(dff_cd_sub[np.in1d(dff_cd_sub['Model'], model_selection)],
                  x="facesvec",
                  y="Curreny density electrolyte",
                  color="Model",
                  animation_frame="fraction")
    fig.update_yaxes(title='Current density of electrolyte [A/m^2]',
                     range=[0.9*min_y, 1.1*max_y])
    fig.update_xaxes(title=' Battery Position [microm] ')
    fig.update_layout(margin={'l': 40, 'b': 80, 't': 10, 'r': 0}, hovermode='closest')
    fig.update_layout(transition_duration=0)
    return fig


@app.callback(
    Output('electrolyte-decd-ani', 'figure'),
    Input('model-selection', 'value'))
def display_animated_graph_elytedivi(model_selection):
    m_select = dff_c_sub[np.in1d(dff_c_sub['Model'], model_selection)]
    max_y = max(m_select["Divergence electrolyte curr dens"])
    min_y = min(m_select["Divergence electrolyte curr dens"])
    fig = px.line(dff_c_sub[np.in1d(dff_c_sub['Model'], model_selection)],
                  x="cellsvec",
                  y="Divergence electrolyte curr dens",
                  color="Model",
                  animation_frame="fraction")
    fig.update_yaxes(title='Divergence of electrolyte current density [A/m^3]',
                     range=[0.9*min_y, 1.1*max_y])
    fig.update_xaxes(title=' Battery Position [microm] ')
    fig.update_layout(margin={'l': 40, 'b': 80, 't': 10, 'r': 0}, hovermode='closest')
    fig.update_layout(transition_duration=500)
    return fig


@app.callback(
    Output('csld_c', 'figure'),
    Input('select_csld_model', 'value'),
    Input('timefraction_slider', 'value'))
def display_animated_subplot_c(model_selection, tf):
    trode = "c"
    partStr = "partTrode{trode}vol{vInd}part{pInd}" + sStr
    r = int(max(dff["Npartc"][dff['Model'] == model_selection]))
    c = int(max(dff["Nvolc"][dff['Model'] == model_selection]))
    fig = make_subplots(rows=r, cols=c, shared_xaxes=True, shared_yaxes=True,
                        x_title='Position (microm)',
                        y_title='Solid Concentrations of Particles in Electrode',
                        row_titles=['Particle ' + str(n) for n in range(1, r+1)],
                        column_titles=['Volume ' + str(n) for n in range(1, c+1)])
    type2c = False
    df_select = dff_csld_sub[dff_csld_sub['Model'] == model_selection]
    df_select = df_select[df_select['time fraction'] == int(tf)]
    if dff["Config trode type"][dff['Model']
                                == model_selection].iloc[0] in constants.one_var_types:
        type2c = False
    elif dff["Config trode type"][dff['Model']
                                  == model_selection].iloc[0] in constants.two_var_types:
        type2c = True
    for rr in range(0, r):
        for cc in range(0, c):
            lens_str = "lens_{vInd}_{pInd}".format(vInd=cc, pInd=rr)
            if type2c is True:
                c1str_base = pfx + partStr.format(trode=trode, pInd=rr, vInd=cc) + "c1"
                c2str_base = pfx + partStr.format(trode=trode, pInd=rr, vInd=cc) + "c2"
                c3str_base = pfx + partStr.format(trode=trode, pInd=rr, vInd=cc) + "cav"
                c1str = c1str_base
                c2str = c2str_base
                c3str = c3str_base
                datax = df_select[lens_str]
                datay1 = df_select[c1str]
                datay2 = df_select[c2str]
                datay3 = df_select[c3str]
                fig.add_trace(
                    trace=go.Scatter(x=datax, y=datay1, line_color='red'),
                    row=rr+1, col=cc+1)
                fig.add_trace(
                    trace=go.Scatter(x=datax, y=datay2, line_color='blue'),
                    row=rr+1, col=cc+1)
                fig.add_trace(
                    trace=go.Scatter(x=datax, y=datay3, line_color='grey'),
                    row=rr+1, col=cc+1)
            else:
                cstr_base = pfx + partStr.format(trode=trode, vInd=cc, pInd=rr) + "c"
                cstr = cstr_base
                datax = df_select[lens_str]
                datay = df_select[cstr]
                fig.add_trace(
                    trace=go.Scatter(x=datax, y=datay, line_color='darkslategray'),
                    row=rr+1, col=cc+1)
    fig.update_yaxes(range=[0,1.01])
    fig.update_layout(height=((r+1)*150), showlegend=False,
                      title='Cathode, time = {time} s'.format(
                      time=round(df_select["time (s)"].iloc[0])))
    return fig


@app.callback(
    Output('csld_a', 'figure'),
    Input('select_csld_model', 'value'),
    Input('timefraction_slider', 'value'))
def display_animated_subplot_a(model_selection, tf):
    try:
        trode = "a"
        partStr = "partTrode{trode}vol{vInd}part{pInd}" + sStr
        r = int(max(dff["Npartc"][dff['Model'] == model_selection]))
        c = int(max(dff["Nvolc"][dff['Model'] == model_selection]))
        fig = make_subplots(rows=r, cols=c, shared_xaxes=True, shared_yaxes=True,
                            x_title='Position (microm)',
                            y_title='Solid Concentrations of Particles in Electrode',
                            row_titles=['Particle ' + str(n) for n in range(1, r+1)],
                            column_titles=['Volume ' + str(n) for n in range(1, c+1)])
        type2c = False
        df_select = dff_csld_sub[dff_csld_sub['Model'] == model_selection]
        df_select = df_select[df_select['time fraction'] == int(tf)]
        if dff["Config trode type"][dff['Model']
                                    == model_selection].iloc[0] in constants.one_var_types:
            type2c = False
        elif dff["Config trode type"][dff['Model']
                                      == model_selection].iloc[0] in constants.two_var_types:
            type2c = True
        for rr in range(0, r):
            for cc in range(0, c):
                lens_str = "lens_{vInd}_{pInd}".format(vInd=cc, pInd=rr)
                if type2c is True:
                    c1str = pfx + partStr.format(trode=trode, pInd=rr, vInd=cc) + "c1"
                    if np.isnan(max(df_select[c1str])):
                        raise ValueError
                    c2str = pfx + partStr.format(trode=trode, pInd=rr, vInd=cc) + "c2"
                    c3str = pfx + partStr.format(trode=trode, pInd=rr, vInd=cc) + "cav"
                    datax = df_select[lens_str]
                    datay1 = df_select[c1str]
                    datay2 = df_select[c2str]
                    datay3 = df_select[c3str]
                    fig.add_trace(
                        trace=go.Scatter(x=datax, y=datay1, line_color='red'),
                        row=rr+1, col=cc+1)
                    fig.add_trace(
                        trace=go.Scatter(x=datax, y=datay2, line_color='blue'),
                        row=rr+1, col=cc+1)
                    fig.add_trace(
                        trace=go.Scatter(x=datax, y=datay3, line_color='grey'),
                        row=rr+1, col=cc+1)
                else:
                    cstr = pfx + partStr.format(trode=trode, pInd=rr, vInd=cc) + "c"
                    if np.isnan(max(df_select[cstr])):
                        raise ValueError
                    datax = df_select[lens_str]
                    datay = df_select[cstr]
                    fig.add_trace(
                        trace=go.Scatter(x=datax, y=datay, line_color='darkslategray'),
                        row=rr+1, col=cc+1)
        fig.update_yaxes(range=[0,1.01])
        fig.update_layout(height=((r+1)*150), showlegend=False,
                          title='Anode, time = {time} s'.format(
                          time=round(df_select["time (s)"].iloc[0]))
                          )
    except ValueError:
        fig = px.line(title='Selected model has no anode')
    return fig


@app.callback(
    Output('cbarline_c', 'figure'),
    Input('select_cbarline_model', 'value')
    )
def update_graph_cbarlinec(select_model):
    trode = "c"
    partStr = "partTrode{trode}vol{{vInd}}part{{pInd}}".format(trode=trode) + sStr
    r = int(max(dff["Npartc"][dff['Model'] == select_model]))
    c = int(max(dff["Nvolc"][dff['Model'] == select_model]))
    fig = make_subplots(rows=r, cols=c, shared_xaxes=True, shared_yaxes=True,
                        x_title='Time (s)', y_title='Particle Average Filling Fraction',
                        row_titles=['Particle ' + str(n) for n in range(1, r+1)],
                        column_titles=['Volume ' + str(n) for n in range(1, c+1)])
    type2c = False
    # this does not work if models with multiple plot types
    if dff["Config trode type"][dff['Model'] == select_model].iloc[0] in constants.one_var_types:
        str_cbar_base = pfx + partStr + "cbar"
    elif dff["Config trode type"][dff['Model'] == select_model].iloc[0] in constants.two_var_types:
        type2c = True
        str1_cbar_base = pfx + partStr + "c1bar"
        str2_cbar_base = pfx + partStr + "c2bar"
    for rr in range(0, r):
        for cc in range(0, c):
            datax = dff['Time (s)'][dff['Model'] == select_model]
            if type2c is True:
                sol1_str = str1_cbar_base.format(pInd=rr, vInd=cc)
                sol2_str = str2_cbar_base.format(pInd=rr, vInd=cc)
                datay = dff[sol1_str][dff['Model'] == select_model]
                datay2 = dff[sol2_str][dff['Model'] == select_model]
                fig.add_trace(
                    trace=go.Scatter(x=datax, y=datay2, line_color='red'),
                    row=rr+1, col=cc+1)
            else:
                sol_str = str_cbar_base.format(pInd=rr, vInd=cc)
                datay = dff[sol_str][dff['Model'] == select_model]
            fig.add_trace(
                trace=go.Scatter(x=datax, y=datay, line_color='darkslategray'),
                row=rr+1, col=cc+1)
    fig.update_yaxes(range=[0,1.01])
    fig.update_layout(height=((r+1)*150), showlegend=False, title='Cathode')
    return fig


@app.callback(
    Output('cbarline_a', 'figure'),
    Input('select_cbarline_model', 'value')
    )
def update_graph_cbarlinea(select_model):
    try:
        trode = "a"
        partStr = "partTrode{trode}vol{{vInd}}part{{pInd}}".format(trode=trode) + sStr
        r = int(max(dff["Nparta"][dff['Model'] == select_model]))
        c = int(max(dff["Nvola"][dff['Model'] == select_model]))
        fig2 = make_subplots(rows=r, cols=c, shared_xaxes=True, shared_yaxes=True,
                             x_title='Time (s)', y_title='Particle Average Filling Fraction',
                             row_titles=['Particle ' + str(n) for n in range(1, r+1)],
                             column_titles=['Volume ' + str(n) for n in range(1, c+1)])
        type2c = False
        if dff["Config trode type"][dff['Model']
                                    == select_model].iloc[0] in constants.one_var_types:
            str_cbar_base = pfx + partStr + "cbar"
        elif dff["Config trode type"][dff['Model']
                                      == select_model].iloc[0] in constants.two_var_types:
            type2c = True
            str1_cbar_base = pfx + partStr + "c1bar"
            str2_cbar_base = pfx + partStr + "c2bar"
        for rr in range(0, r):
            for cc in range(0, c):
                datax = dff['Time (s)'][dff['Model'] == select_model]
                if type2c is True:
                    sol1_str = str1_cbar_base.format(pInd=rr, vInd=cc)
                    sol2_str = str2_cbar_base.format(pInd=rr, vInd=cc)
                    datay = dff[sol1_str][dff['Model'] == select_model]
                    datay2 = dff[sol2_str][dff['Model'] == select_model]
                    fig2.add_trace(
                        trace=go.Scatter(x=datax, y=datay2, line_color='red'),
                        row=rr+1, col=cc+1)
                else:
                    sol_str = str_cbar_base.format(pInd=rr, vInd=cc)
                    datay = dff[sol_str][dff['Model'] == select_model]
                fig2.add_trace(
                    trace=go.Scatter(x=datax, y=datay, line_color='darkslategray'),
                    row=rr+1, col=cc+1)
        fig2.update_yaxes(range=[0,1.01])
        fig2.update_layout(height=((r+1)*150), showlegend=False, title='Anode')
    except ValueError:
        fig2 = px.line(title='Selected model has no anode')
    return fig2


if __name__ == '__main__':
    app.run_server(debug=True)