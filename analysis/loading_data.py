import logging
import numpy as np
import os
import pandas as pd

logging.basicConfig(filename='manual_inhibition_analysis.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DataLoadLogger')


def load_all_data(path_names):
    full_data_uncorrected = raw_jatosdata_to_csv(path_names['source'], path_names['incomplete'], path_names['extra'],
                                                 path_names['extra_questions'], path_names['out_file'])
    full_data_corrected = manual_file_correction(full_data_uncorrected)
    full_data_corrected.to_csv(path_names['out_file'], index=False)
    logger.info(f"data frames were combined and saved at {path_names['out_file']}")

    return full_data_corrected


def raw_jatosdata_to_csv(source_file, incomplete_path, extra_file, extra_questions, destiny_file):
    try:
        if os.path.getmtime(source_file) > os.path.getmtime(destiny_file) or os.path.getmtime(
                extra_file) > os.path.getmtime(destiny_file):
            logger.info('The raw data file was updated - Loading again.')
        else:
            logger.info('The file is up-to-date.')
            return pd.read_csv(destiny_file)

    except FileNotFoundError:
        logger.info('Creating a new data file from raw json.')

    # load and append incomplete files
    source_to_pandas = load_rawjson(source_file)
    incomplete_main = load_json_from_path(incomplete_path)
    extra_to_pandas = load_rawjson(extra_file)
    extra_questionnaire = pd.read_csv(extra_questions)
    logger.info(f'data was imported from file {extra_questions}')
    source_to_pandas = pd.concat([source_to_pandas, incomplete_main, extra_to_pandas, extra_questionnaire],
                                 ignore_index=True)
    return source_to_pandas


def load_rawjson(file):
    data = {}
    with open(file) as f:
        # unpack the data
        for ses, jf in enumerate(f):
            # save it to a data frame
            df = pd.read_json(jf)
            try:
                data = pd.concat([data, df], axis=0)
            except:
                data = df
    logger.info(f'data was imported from file: {file}.')
    return data


def load_json_from_path(pathname):
    data = pd.DataFrame()

    for file in os.listdir(pathname):
        df = pd.read_json(pathname + file)
        data = pd.concat([data, df], ignore_index=True)

    logger.info(f'data was imported from path: {pathname}.')
    return data


def manual_file_correction(experiment_data):
    """
    This is a hardcoded and purely manual correction/data cleaning procedure
    """
    # In this part of the manual correction, we add missing session numbers
    missing_session_number = np.where(experiment_data.session_number.isnull() & experiment_data.success == 1)
    missing_session_data = experiment_data.iloc[missing_session_number]
    missing_session_data = missing_session_data[missing_session_data.trial_type == 'canvas-mi-serial']
    logger.info(f'{len(missing_session_data)} trials with missing session data were found')
    logger.info('comment from CK: this is because we hard-coded the parameters for trials that were repeated'
                 'in extra session. For these trials I forgot to hard-code the session number.')
    if len(missing_session_data) > 0:
        session_3_id = missing_session_data[missing_session_data.trialID == 185].index
        session_4_id = missing_session_data[missing_session_data.trialID == 8].index

        experiment_data.loc[session_3_id, 'session_number'] = 3
        experiment_data.loc[session_4_id, 'session_number'] = 4
        logger.info('Missing session numbers were added manually')

    # In this part of the manual correction, we add session and study ids
    session_id_2 = '621fb3bfd880d8d0e1fd44ae'
    session_id_3 = '622091b3a577c6d522b391cb'
    session_id_4 = '6220e28a584f925fcdfc9ded'

    study_id_2 = '6216b9f6fa734c0a4acefab5'
    study_id_3 = '6216bb63e6411c3f058a4480'
    study_id_4 = '6216bbcec318b5df4e482581'

    subject_data = experiment_data[experiment_data.prolific_id == '5ae0b548e0feeb0001cafc45']

    ids_2 = subject_data[subject_data.session_number == 2].index
    ids_3 = subject_data[subject_data.session_number == 3].index
    ids_4 = subject_data[subject_data.session_number == 4].index

    experiment_data.loc[ids_2, 'session_id'] = session_id_2
    experiment_data.loc[ids_3, 'session_id'] = session_id_3
    experiment_data.loc[ids_4, 'session_id'] = session_id_4

    experiment_data.loc[ids_2, 'study_id'] = study_id_2
    experiment_data.loc[ids_3, 'study_id'] = study_id_3
    experiment_data.loc[ids_4, 'study_id'] = study_id_4

    logger.info('missing session ids and study ids were added manually')

    # In this part of the manual correction, we remove two dropped participants
    # remove two participants that were excluded/dropped out
    drop_outs = ['6129dc084c55f609fd62f0bc', '5f9f4660d0edb75784c68223']
    for idx in drop_outs:
        experiment_data = experiment_data[experiment_data.prolific_id != idx]
    logger.info(f'data from participants {drop_outs} was excluded from the final data set.')

    return experiment_data
