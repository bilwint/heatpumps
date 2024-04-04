# -*- coding: utf-8 -*-
"""
Created on Thu Jun  2 09:54:24 2022

@author: Jonas Freißmann
"""

import json
import os

import numpy as np
import pandas as pd
import streamlit as st
import variables as var
from simulation import run_design, run_partload


def switch2design():
    """Switch to design simulation tab."""
    st.session_state.select = 'Auslegung'


def switch2partload():
    """Switch to partload simulation tab."""
    st.session_state.select = 'Teillast'


def info_df(label, refrigs):
    """Create Dataframe with info of chosen refrigerant."""
    df_refrig = pd.DataFrame(
        columns=['Typ', 'T_NBP', 'T_krit', 'p_krit', 'SK', 'ODP', 'GWP']
        )
    df_refrig.loc[label, 'Typ'] = refrigs[label]['type']
    df_refrig.loc[label, 'T_NBP'] = str(refrigs[label]['T_NBP'])
    df_refrig.loc[label, 'T_krit'] = str(refrigs[label]['T_crit'])
    df_refrig.loc[label, 'p_krit'] = str(refrigs[label]['p_crit'])
    df_refrig.loc[label, 'SK'] = refrigs[label]['ASHRAE34']
    df_refrig.loc[label, 'ODP'] = str(refrigs[label]['ODP'])
    df_refrig.loc[label, 'GWP'] = str(refrigs[label]['GWP100'])

    return df_refrig

root_path = os.path.abspath(__file__)
src_path = os.path.join(root_path, '..', 'src')

# %% Initialisation
refrigpath = os.path.join(src_path, 'refrigerants.json')
with open(refrigpath, 'r', encoding='utf-8') as file:
    refrigerants = json.load(file)

st.set_page_config(
    layout='wide',
    page_title='Wärmepumpen Dashboard',
    page_icon=os.path.join(src_path, 'img', 'page_icon_ZNES.png')
    )

# %% Sidebar
with st.sidebar:
    st.image(os.path.join(src_path, 'img', 'Logo_ZNES.png'))

    mode = st.selectbox('', ['Auslegung', 'Teillast'], key='select')

    st.markdown("""---""")

    # %% Design
    if mode == 'Auslegung':
        st.header('Auslegung der Wärmepumpe')

        with st.expander('Setup'):
            base_topology = st.selectbox(
                'Grundtopologie',
                var.base_topologies,
                index=0, key='base_topology'
            )

            models = []
            for model, mdata in var.hp_models.items():
                if mdata['base_topology'] == base_topology:
                    models.append(mdata['display_name'])

            model_name = st.selectbox(
                'Wärmepumpenmodell', models, index=0, key='model'
            )

            for model, mdata in var.hp_models.items():
                correct_base = mdata['base_topology'] == base_topology
                correct_model_name = mdata['display_name'] == model_name
                if correct_base and correct_model_name:
                    hp_model = mdata
                    hp_model_name = model
                    break

            parampath = os.path.join(
                __file__, '..', 'models', 'input',
                f'params_hp_{hp_model_name}.json'
            )
            with open(parampath, 'r', encoding='utf-8') as file:
                params = json.load(file)

        if hp_model['nr_ihx'] > 0:
            with st.expander('Interne Wärmerübertragung'):
                dT_ihx = {}
                for i in range(1, hp_model['nr_ihx']+1):
                     dT_ihx[i] = st.slider(
                        f'Nr. {i}: Überhitzung/Unterkühlung', value=5, min_value=0,
                        max_value=25, format='%d°C', key=f'dT_ihx{i}'
                        )

        with st.expander('Kältemittel'):
            if hp_model['nr_cycles'] == 1:
                refrig_index = None
                for ridx, (rlabel, rdata) in enumerate(refrigerants.items()):
                    if rlabel == params['setup']['refrig']:
                        refrig_index = ridx
                        break
                    elif rdata['CP'] == params['setup']['refrig']:
                        refrig_index = ridx
                        break

                refrig_label = st.selectbox(
                    '', refrigerants.keys(), index=refrig_index,
                    key='refrigerant'
                    )
                params['setup']['refrig'] = refrigerants[refrig_label]['CP']
                params['fluids']['wf'] = refrigerants[refrig_label]['CP']
                df_refrig = info_df(refrig_label, refrigerants)

            elif hp_model['nr_cycles'] == 2:
                refrig1_index = None
                for ridx, (rlabel, rdata) in enumerate(refrigerants.items()):
                    if rlabel == params['setup']['refrig1']:
                        refrig1_index = ridx
                        break
                    elif rdata['CP'] == params['setup']['refrig1']:
                        refrig1_index = ridx
                        break

                refrig1_label = st.selectbox(
                    '1. Kältemittel', refrigerants.keys(),
                    index=refrig1_index, key='refrigerant1'
                    )
                params['setup']['refrig1'] = refrigerants[refrig1_label]['CP']
                params['fluids']['wf1'] = refrigerants[refrig1_label]['CP']
                df_refrig1 = info_df(refrig1_label, refrigerants)

                refrig2_index = None
                for ridx, (rlabel, rdata) in enumerate(refrigerants.items()):
                    if rlabel == params['setup']['refrig2']:
                        refrig2_index = ridx
                        break
                    elif rdata['CP'] == params['setup']['refrig2']:
                        refrig2_index = ridx
                        break


                refrig2_label = st.selectbox(
                    '2. Kältemittel', refrigerants.keys(),
                    index=refrig2_index, key='refrigerant2'
                    )
                params['setup']['refrig2'] = refrigerants[refrig2_label]['CP']
                params['fluids']['wf2'] = refrigerants[refrig2_label]['CP']
                df_refrig2 = info_df(refrig2_label, refrigerants)

        if hp_model['nr_cycles'] == 1:
            T_crit = int(np.floor(refrigerants[refrig_label]['T_crit']))
        elif hp_model['nr_cycles'] == 2:
            T_crit = int(np.floor(refrigerants[refrig2_label]['T_crit']))

        st.session_state.T_crit = T_crit

        with st.expander('Thermische Nennleistung'):
            params['cons']['Q'] = st.number_input(
                'Wert in MW', value=abs(params['cons']['Q']/1e6),
                step=0.1, key='Q_N'
                )
            params['cons']['Q'] *= -1e6

        with st.expander('Wärmequelle'):
            params['B1']['T'] = st.slider(
                'Temperatur Vorlauf', min_value=0, max_value=T_crit,
                value=params['B1']['T'], format='%d°C', key='T_heatsource_ff'
                )
            params['B2']['T'] = st.slider(
                'Temperatur Rücklauf', min_value=0, max_value=T_crit,
                value=params['B2']['T'], format='%d°C', key='T_heatsource_bf'
                )

            invalid_temp_diff = params['B2']['T'] >= params['B1']['T']
            if invalid_temp_diff:
                st.error(
                    'Die Rücklauftemperatur muss niedriger sein, als die '
                    + 'Vorlauftemperatur.'
                    )
            params['B1']['p'] = st.slider(
                'Druck', min_value=1.0, max_value=20.0,
                value=float(params['B1']['p']), step=0.1, format='%f bar',
                key='p_heatsource_ff'
                )

        # TODO: Aktuell wird T_mid im Modell als Mittelwert zwischen von Ver-
        #       dampfungs- und Kondensationstemperatur gebildet. An sich wäre
        #       es analytisch sicher interessant den Wert selbst festlegen zu
        #       können.
        # if hp_model['nr_cycles'] == 2:
        #     with st.expander('Zwischenwärmeübertrager'):
        #         param['design']['T_mid'] = st.slider(
        #             'Mittlere Temperatur', min_value=0, max_value=T_crit,
        #             value=40, format='%d°C', key='T_mid'
        #             )

        with st.expander('Wärmesenke'):
            params['C3']['T'] = st.slider(
                'Temperatur Vorlauf', min_value=0, max_value=T_crit,
                value=params['C3']['T'], format='%d°C', key='T_consumer_ff'
                )
            params['C0']['T'] = st.slider(
                'Temperatur Rücklauf', min_value=0, max_value=T_crit,
                value=params['C0']['T'], format='%d°C', key='T_consumer_bf'
                )

            invalid_temp_diff = params['C0']['T'] >= params['C3']['T']
            if invalid_temp_diff:
                st.error(
                    'Die Rücklauftemperatur muss niedriger sein, als die '
                    + 'Vorlauftemperatur.'
                    )
            invalid_temp_diff = params['C0']['T'] <= params['B1']['T']
            if invalid_temp_diff:
                st.error(
                    'Die Temperatur der Wärmesenke muss höher sein, als die '
                    + 'der Wärmequelle.'
                    )
            params['C3']['p'] = st.slider(
                'Druck', min_value=1.0, max_value=20.0,
                value=float(params['C3']['p']), step=0.1, format='%f bar',
                key='p_consumer_ff'
                )

        st.session_state.hp_params = params

        run_sim = st.button('🧮 Auslegung ausführen')
        # run_sim = True
    # autorun = st.checkbox('AutoRun Simulation', value=True)

    # %% Offdesign
    if mode == 'Teillast':
        params = st.session_state.hp_params
        st.header('Teillastsimulation der Wärmepumpe')

        with st.expander('Teillast'):
            (params['offdesign']['partload_min'],
             params['offdesign']['partload_max']) = st.slider(
                'Bezogen auf Nennmassenstrom',
                min_value=0, max_value=120, step=5,
                value=(30, 100), format='%d%%', key='pl_slider'
                )

            params['offdesign']['partload_min'] /= 100
            params['offdesign']['partload_max'] /= 100

            params['offdesign']['partload_steps'] = int(np.ceil(
                    (params['offdesign']['partload_max']
                     - params['offdesign']['partload_min'])
                    / 0.1
                    ) + 1)

        with st.expander('Wärmequelle'):
            type_hs = st.radio(
                '', ('Konstant', 'Variabel'), index=1, horizontal=True,
                key='temp_hs'
                )
            if type_hs == 'Konstant':
                params['offdesign']['T_hs_ff_start'] = (
                    st.session_state.hp.params['B1']['T']
                    )
                params['offdesign']['T_hs_ff_end'] = (
                    params['offdesign']['T_hs_ff_start'] + 1
                    )
                params['offdesign']['T_hs_ff_steps'] = 1

                text = (
                    f'Temperatur <p style="color:{var.st_color_hex}">'
                    + f'{params["offdesign"]["T_hs_ff_start"]} °C'
                    + r'</p>'
                    )
                st.markdown(text, unsafe_allow_html=True)

            elif type_hs == 'Variabel':
                params['offdesign']['T_hs_ff_start'] = st.slider(
                    'Starttemperatur',
                    min_value=0, max_value=st.session_state.T_crit, step=1,
                    value=int(
                        st.session_state.hp.params['B1']['T']
                        - 5
                        ),
                    format='%d°C', key='T_hs_ff_start_slider'
                    )
                params['offdesign']['T_hs_ff_end'] = st.slider(
                    'Endtemperatur',
                    min_value=0, max_value=st.session_state.T_crit, step=1,
                    value=int(
                        st.session_state.hp.params['B1']['T']
                        + 5
                        ),
                    format='%d°C', key='T_hs_ff_end_slider'
                    )
                params['offdesign']['T_hs_ff_steps'] = int(np.ceil(
                    (params['offdesign']['T_hs_ff_end']
                     - params['offdesign']['T_hs_ff_start'])
                    / 3
                    ) + 1)

        with st.expander('Wärmesenke'):
            type_cons = st.radio(
                '', ('Konstant', 'Variabel'), index=1, horizontal=True,
                key='temp_cons'
                )
            if type_cons == 'Konstant':
                params['offdesign']['T_cons_ff_start'] = (
                    st.session_state.hp.params['C3']['T']
                    )
                params['offdesign']['T_cons_ff_end'] = (
                    params['offdesign']['T_cons_ff_start'] + 1
                    )
                params['offdesign']['T_cons_ff_steps'] = 1

                text = (
                    f'Temperatur <p style="color:{var.st_color_hex}">'
                    + f'{params["offdesign"]["T_cons_ff_start"]} °C'
                    + r'</p>'
                    )
                st.markdown(text, unsafe_allow_html=True)

            elif type_cons == 'Variabel':
                params['offdesign']['T_cons_ff_start'] = st.slider(
                    'Starttemperatur',
                    min_value=0, max_value=st.session_state.T_crit, step=1,
                    value=int(
                        st.session_state.hp.params['C3']['T']
                        - 10
                        ),
                    format='%d°C', key='T_cons_ff_start_slider'
                    )
                params['offdesign']['T_cons_ff_end'] = st.slider(
                    'Endtemperatur',
                    min_value=0, max_value=st.session_state.T_crit, step=1,
                    value=int(
                        st.session_state.hp.params['C3']['T']
                        + 10
                        ),
                    format='%d°C', key='T_cons_ff_end_slider'
                    )
                params['offdesign']['T_cons_ff_steps'] = int(np.ceil(
                    (params['offdesign']['T_cons_ff_end']
                     - params['offdesign']['T_cons_ff_start'])
                    / 3
                    ) + 1)

        st.session_state.hp_params = params
        run_pl_sim = st.button('🧮 Teillast simulieren')

# %% Main Content
st.title('Wärmepumpensimulator 3k Pro™')

if mode == 'Auslegung':
    # %% Design Simulation
    if not run_sim and 'hp' not in st.session_state:
        # %% Landing Page
        st.write(
            """
            Der Wärmepumpensimulator 3k Pro™ ist eine leistungsfähige
            Simulationssoftware zur Auslegung und Teillastbetrachtung von
            Wärmepumpen.
            """
            )

        st.write(
            """
            Sie befinden sich auf der Oberfläche zur Auslegungssimulation
            Ihrer Wärmepumpe. Dazu sind links in der Sidebar neben der
            Dimensionierung und der Wahl des zu verwendenden Kältemittels
            verschiedene zentrale Parameter des Kreisprozesse vorzugeben.
            """
            )

        st.write(
            """
            Dies sind zum Beispiel die Temperaturen der Wärmequelle und -senke,
            aber auch die dazugehörigen Netzdrücke. Darüber hinaus kann
            optional ein interner Wärmeübertrager hinzugefügt werden. Dazu ist
            weiterhin die resultierende Überhitzung des verdampften
            Kältemittels vorzugeben.
            """
            )

        st.write(
            """
            Ist die Auslegungssimulation erfolgreich abgeschlossen, werden die
            generierten Ergebnisse graphisch in Zustandsdiagrammen
            aufgearbeitet und quantifiziert. Die zentralen Größen wie die
            Leistungszahl (COP) sowie die relevanten Wärmeströme und Leistung
            werden aufgeführt. Darüber hinaus werden die thermodynamischen
            Zustandsgrößen in allen Prozessschritten tabellarisch aufgelistet.
            """
            )

        st.write(
            """
            Im Anschluss an die Auslegungsimulation erscheint ein Knopf zum
            Wechseln in die Teillastoberfläche. Dies kann ebenfalls über das
            Dropdownmenü in der Sidebar erfolgen. Informationen zur
            Durchführung der Teillastsimulationen befindet sich auf der
            Startseite dieser Oberfläche.
            """
            )

        st.markdown("""---""")

        with st.expander('Verwendete Software'):
            st.info(
                """
                #### Verwendete Software:

                Zur Modellerstellung und Berechnung der Simulationen wird die
                Open Source Software TESPy verwendet. Des Weiteren werden
                eine Reihe weiterer Pythonpakete zur Datenverarbeitung,
                -aufbereitung und -visualisierung genutzt.

                ---

                #### TESPy:

                TESPy (Thermal Engineering Systems in Python) ist ein
                leistungsfähiges Simulationswerkzeug für thermische
                Verfahrenstechnik, zum Beispiel für Kraftwerke,
                Fernwärmesysteme oder Wärmepumpen. Mit dem TESPy-Paket ist es
                möglich, Anlagen auszulegen und den stationären Betrieb zu
                simulieren. Danach kann das Teillastverhalten anhand der
                zugrundeliegenden Charakteristiken für jede Komponente der
                Anlage ermittelt werden. Die komponentenbasierte Struktur in
                Kombination mit der Lösungsmethode bieten eine sehr hohe
                Flexibilität hinsichtlich der Anlagentopologie und der
                Parametrisierung. Weitere Informationen zu TESPy sind in dessen
                [Onlinedokumentation](https://tespy.readthedocs.io) in
                englischer Sprache zu finden.

                #### Weitere Pakete:

                - [Streamlit](https://docs.streamlit.io) (Graphische Oberfläche)
                - [NumPy](https://numpy.org) (Datenverarbeitung)
                - [pandas](https://pandas.pydata.org) (Datenverarbeitung)
                - [SciPy](https://scipy.org/) (Interpolation)
                - [scikit-learn](https://scikit-learn.org) (Regression)
                - [Matplotlib](https://matplotlib.org) (Datenvisualisierung)
                - [FluProDia](https://fluprodia.readthedocs.io) (Datenvisualisierung)
                - [CoolProp](http://www.coolprop.org) (Stoffdaten)
                """
                )

        with st.expander('Disclaimer'):
            st.warning(
                """
                #### Simulationsergebnisse:

                Numerische Simulationen sind Berechnungen mittels geeigneter
                Iterationsverfahren in Bezug auf die vorgegebenen und gesetzten
                Randbedingungen und Parameter. Eine Berücksichtigung aller
                möglichen Einflüsse ist in Einzelfällen nicht möglich, so dass
                Abweichungen zu Erfahrungswerten aus Praxisanwendungen
                entstehen können und bei der Bewertung berücksichtigt werden
                müssen. Die Ergebnisse geben hinreichenden bis genauen
                Aufschluss über das prinzipielle Verhalten, den COP und
                Zustandsgrößen in den einzelnen Komponenten der Wärmepumpe.
                Dennoch sind alle Angaben und Ergebnisse ohne Gewähr.
                """
                )

    if run_sim:
        # %% Run Design Simulation
        with st.spinner('Simulation wird durchgeführt...'):
            st.session_state.hp = run_design(hp_model_name, params)

            st.success(
                'Die Simulation der Wärmepumpenauslegung war erfolgreich.'
                )

    if run_sim or 'hp' in st.session_state:
        # %% Results
        with st.spinner('Ergebnisse werden visualisiert...'):

            stateconfigpath = os.path.join(
                __file__, '..', 'models', 'input', 'state_diagram_config.json'
                )
            with open(stateconfigpath, 'r', encoding='utf-8') as file:
                config = json.load(file)
            if hp_model['nr_cycles'] == 1:
                if st.session_state.hp.params['setup']['refrig'] in config:
                    state_props = config[
                        st.session_state.hp.params['setup']['refrig']
                        ]
                else:
                    state_props = config['MISC']

            st.header('Ergebnisse der Auslegung')

            col1, col2, col3, col4 = st.columns(4)
            col1.metric('COP', round(st.session_state.hp.cop, 2))
            col2.metric(
                'Q_dot_ab',
                f"{st.session_state.hp.buses['heat output'].P.val*-1e-6:.2f} MW"
                )
            col3.metric(
                'P_zu',
                f"{st.session_state.hp.buses['power input'].P.val/1e6:.2f} MW"
                )
            Q_dot_zu = abs(
                st.session_state.hp.comps['evap'].Q.val/1e6
                )
            col4.metric('Q_dot_zu', f'{Q_dot_zu:.2f} MW')

            with st.expander('Zustandsdiagramme', expanded=True):
                # %% State Diagrams
                col_left, _, col_right = st.columns([0.495, 0.01, 0.495])
                _, slider_left, _, slider_right, _ = (
                    st.columns([0.5, 8, 1, 8, 0.5])
                    )

                with col_left:
                    # %% Log(p)-h-Diagram
                    st.subheader('Log(p)-h-Diagramm')
                    diagram_placeholder = st.empty()

                with slider_left:
                    if hp_model['nr_cycles'] == 1:
                        xmin, xmax = st.slider(
                            'X-Achsen Begrenzung',
                            min_value=0, max_value=3000, step=100,
                            value=(
                                state_props['h']['min'],
                                state_props['h']['max']
                                ),
                            format='%d kJ/kg',
                            key='ph_xslider'
                            )
                        ymin, ymax = st.slider(
                            'Y-Achsen Begrenzung',
                            min_value=-3, max_value=3,
                            value=(0, 2), format='10^%d bar', key='ph_yslider'
                            )
                        ymin, ymax = 10**ymin, 10**ymax
                    elif hp_model['nr_cycles'] == 2:
                        xmin1, xmax1 = st.slider(
                            'X-Achsen Begrenzung (Kreislauf 1)',
                            min_value=0, max_value=3000, step=100,
                            value=(100, 2200), format='%d kJ/kg',
                            key='ph_x1slider'
                            )
                        ymin1, ymax1 = st.slider(
                            'Y-Achsen Begrenzung (Kreislauf 1)',
                            min_value=-3, max_value=3,
                            value=(0, 2), format='10^%d bar',
                            key='ph_y1slider'
                            )
                        ymin1, ymax1 = 10**ymin1, 10**ymax1
                        xmin2, xmax2 = st.slider(
                            'X-Achsen Begrenzung (Kreislauf 2)',
                            min_value=0, max_value=3000, step=100,
                            value=(100, 2200), format='%d kJ/kg',
                            key='ph_x2slider'
                            )
                        ymin2, ymax2 = st.slider(
                            'Y-Achsen Begrenzung (Kreislauf 2)',
                            min_value=-3, max_value=3,
                            value=(0, 2), format='10^%d bar',
                            key='ph_y2slider'
                            )
                        ymin2, ymax2 = 10**ymin2, 10**ymax2

                with col_left:
                    if hp_model['nr_cycles'] == 1:
                        diagram = st.session_state.hp.generate_state_diagram(
                            diagram_type='logph',
                            xlims=(xmin, xmax), ylims=(ymin, ymax),
                            return_diagram=True, display_info=False,
                            open_file=False, savefig=False
                            )
                        diagram_placeholder.pyplot(diagram.fig)
                    elif hp_model['nr_cycles'] == 2:
                        diagram1, diagram2 = st.session_state.hp.generate_state_diagram(
                            diagram_type='logph',
                            xlims=((xmin1, xmax1), (xmin2, xmax2)),
                            ylims=((ymin1, ymax1), (ymin2, ymax2)),
                            return_diagram=True, display_info=False,
                            savefig=False, open_file=False
                            )
                        diagram_placeholder.pyplot(diagram1.fig)
                        diagram_placeholder.pyplot(diagram2.fig)

                with col_right:
                    # %% T-s-Diagram
                    st.subheader('T-s-Diagramm')
                    diagram_placeholder = st.empty()

                with slider_right:
                    if hp_model['nr_cycles'] == 1:
                        xmin, xmax = st.slider(
                            'X-Achsen Begrenzung',
                            min_value=0, max_value=10000, step=100,
                            value=(
                                state_props['s']['min'],
                                state_props['s']['max']
                                ),
                            format='%d kJ/(kgK)',
                            key='ts_xslider'
                            )
                        ymin, ymax = st.slider(
                            'Y-Achsen Begrenzung',
                            min_value=-150, max_value=500,
                            value=(
                                state_props['T']['min'],
                                state_props['T']['max']
                                ),
                            format='%d °C', key='ts_yslider'
                            )
                    elif hp_model['nr_cycles'] == 2:
                        xmin1, xmax1 = st.slider(
                            'X-Achsen Begrenzung (Kreislauf 1)',
                            min_value=0, max_value=3000, step=100,
                            value=(100, 2200), format='%d kJ/kg',
                            key='ts_x1slider'
                            )
                        ymin1, ymax1 = st.slider(
                            'Y-Achsen Begrenzung (Kreislauf 1)',
                            min_value=-3, max_value=3,
                            value=(0, 2), format='10^%d bar',
                            key='ts_y1slider'
                            )
                        ymin1, ymax1 = 10**ymin1, 10**ymax1
                        xmin2, xmax2 = st.slider(
                            'X-Achsen Begrenzung (Kreislauf 2)',
                            min_value=0, max_value=3000, step=100,
                            value=(100, 2200), format='%d kJ/kg',
                            key='ts_x2slider'
                            )
                        ymin2, ymax2 = st.slider(
                            'Y-Achsen Begrenzung (Kreislauf 2)',
                            min_value=-3, max_value=3,
                            value=(0, 2), format='10^%d bar',
                            key='ts_y2slider'
                            )
                        ymin2, ymax2 = 10**ymin2, 10**ymax2

                with col_right:
                    if hp_model['nr_cycles'] == 1:
                        diagram = st.session_state.hp.generate_state_diagram(
                            diagram_type='Ts',
                            xlims=(xmin, xmax), ylims=(ymin, ymax),
                            return_diagram=True, display_info=False,
                            open_file=False, savefig=False
                            )
                        diagram_placeholder.pyplot(diagram.fig)
                    elif hp_model['nr_cycles'] == 2:
                        diagram1, diagram2 = st.session_state.hp.generate_state_diagram(
                            diagram_type='Ts',
                            xlims=((xmin1, xmax1), (xmin2, xmax2)),
                            ylims=((ymin1, ymax1), (ymin2, ymax2)),
                            return_diagram=True, display_info=False,
                            savefig=False, open_file=False
                            )
                        diagram_placeholder.pyplot(diagram1.fig)
                        diagram_placeholder.pyplot(diagram2.fig)

            with st.expander('Zustandsgrößen'):
                # %% State Quantities
                state_quantities = (
                    st.session_state.hp.nw.results['Connection'].copy()
                    )
                try:
                    state_quantities['water'] = (
                        state_quantities['water'].apply(bool)
                        )
                except KeyError:
                    state_quantities['H2O'] = (
                        state_quantities['H2O'].apply(bool)
                        )
                if hp_model['nr_cycles'] == 1:
                    refrig = st.session_state.hp.params['setup']['refrig']
                    state_quantities[refrig] = (
                        state_quantities[refrig].apply(bool)
                        )
                elif hp_model['nr_cycles'] == 2:
                    refrig1 = st.session_state.hp.params['setup']['refrig1']
                    state_quantities[refrig1] = (
                        state_quantities[refrig1].apply(bool)
                        )
                    refrig2 = st.session_state.hp.params['setup']['refrig2']
                    state_quantities[refrig2] = (
                        state_quantities[refrig2].apply(bool)
                        )
                if 'Td_bp' in state_quantities.columns:
                    del state_quantities['Td_bp']
                for col in state_quantities.columns:
                    if state_quantities[col].dtype == np.float64:
                        state_quantities[col] = state_quantities[col].apply(
                            lambda x: f'{x:.5}'
                            )
                state_quantities['x'] = state_quantities['x'].apply(
                    lambda x: '-' if float(x) < 0 else x
                    )
                state_quantities.rename(
                    columns={
                        'm': 'm in kg/s',
                        'p': 'p in bar',
                        'h': 'h in kJ/kg',
                        'T': 'T in °C',
                        'v': 'v in m³/kg',
                        'vol': 'vol in m³/s',
                        's': 's in kJ/(kgK)'
                        },
                    inplace=True)
                st.dataframe(data=state_quantities, use_container_width=True)

            with st.expander('Topologie & Kältemittel'):
                # %% Topology & Refrigerant
                col_left, col_right = st.columns([1, 4])

                with col_left:
                    st.subheader('Topologie')

                    # TODO: Topologien einfügen und darstellen
                    # top_file = os.path.join(src_path, 'img', 'topologies', 'hp')
                    # if hp_model['nr_cycles'] == 1:
                    #     if params['design']['int_heatex']:
                    #         top_file = os.path.join(top_file, '_ih.png')
                    #     # elif param['design']['intercooler']:
                    #     #     top_file = os.path.join(top_file, '_ic.png')
                    #     else:
                    #         top_file = os.path.join(top_file, '.png')
                    # elif hp_model['nr_cycles'] == 2:
                    #     top_file = os.path.join(top_file, '_2_ih.png')

                    # st.image(top_file)

                with col_right:
                    st.subheader('Kältemittel')

                    if hp_model['nr_cycles'] == 1:
                        st.table(df_refrig)
                    elif hp_model['nr_cycles'] == 2:
                        st.table(df_refrig1)
                        st.table(df_refrig2)

                    st.write(
                        """
                        Alle Stoffdaten und Klassifikationen aus
                        [CoolProp](http://www.coolprop.org) oder
                        [Arpagaus et al. (2018)](https://doi.org/10.1016/j.energy.2018.03.166)
                        """
                        )

            with st.expander('Ökonomische Bewertung'):
                # %% Eco Results
                # TODO: Komponentenkosten berechnen und Ergebnisse darstellen.
                # TODO: Man müsste auch die Annahmen dafür hier angeben.
                st.write('Ökonomische Bewertung an dieser Stelle einfügen.')

            st.info(
                'Um die Teillast zu berechnen, drücke auf "Teillast '
                + 'simulieren".'
                )

            run_pl = st.button('Teillast simulieren', on_click=switch2partload)

if mode == 'Teillast':
    # %% Offdesign Simulation
    st.header('Betriebscharakteristik')

    if not run_pl_sim and 'partload_char' not in st.session_state:
        # %% Landing Page
        st.write(
            '''
            Parametrisierung der Teillastberechnung:
            + Prozentualer Anteil Teillast
            + Bereich der Quelltemperatur
            + Bereich der Senkentemperatur
            '''
            )

    if run_pl_sim:
        # %% Run Offdesign Simulation
        with st.spinner(
                'Teillastsimulation wird durchgeführt... Dies kann eine '
                + 'Weile dauern.'
                ):
            st.session_state.hp, st.session_state.partload_char = (
                run_partload(st.session_state.hp)
                )
            # st.session_state.partload_char = pd.read_csv(
            #     'partload_char.csv', index_col=[0, 1, 2], sep=';'
            #     )
            st.success(
                'Die Simulation der Wärmepumpencharakteristika war '
                + 'erfolgreich.'
                )

    if run_pl_sim or 'partload_char' in st.session_state:
        # %% Results
        with st.spinner('Ergebnisse werden visualisiert...'):

            with st.expander('Diagramme', expanded=True):
                col_left, col_right = st.columns(2)

                try:
                    with col_left:
                        figs, axes = st.session_state.hp.plot_partload_char(
                            st.session_state.partload_char, cmap_type='COP',
                            return_fig_ax=True
                            )
                        pl_cop_placeholder = st.empty()
                        T_select_cop = st.select_slider(
                            'Quellentemperatur',
                            options=[k for k in figs.keys()],
                            value=float(np.median(
                                [k for k in figs.keys()]
                                )),
                            key='pl_cop_slider'
                            )
                        pl_cop_placeholder.pyplot(figs[T_select_cop])

                    with col_right:
                        figs, axes = st.session_state.hp.plot_partload_char(
                            st.session_state.partload_char, cmap_type='T_cons_ff',
                            return_fig_ax=True
                            )
                        pl_T_cons_ff_placeholder = st.empty()
                        T_select_T_cons_ff = st.select_slider(
                            'Quellentemperatur',
                            options=[k for k in figs.keys()],
                            value=float(np.median(
                                [k for k in figs.keys()]
                                )),
                            key='pl_T_cons_ff_slider'
                            )
                        pl_T_cons_ff_placeholder.pyplot(figs[T_select_T_cons_ff])
                except AttributeError:
                    # TODO: `plot_partload_char` Methode aus generischer Klasse
                    #       aufräumen und in HeatPumpBase implementieren.
                    st.warning('Teillastdiagramme aktuell nicht implementiert.')
