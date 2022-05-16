import logging
import numpy as np
import pandas as pd
import helper_funcs as helper

logging.basicConfig(filename='manual_inhibition_analysis.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('PreprocessingLogger')


# Library for preprocessing of data from the manual inhibition experiment
def preprocessing_pipeline(data_file_name):
    """
    This is the full preprocessing pipeline, performing temporal and spatial alignments.
    """
    data = pd.read_csv(data_file_name)

    # split the data
    calibration_data, training_data, main_session_data, \
        trial_data, question_data = split_data(data)

    trial_data = ensure_formats(trial_data)
    trial_data = perform_time_alignments(trial_data)

    # get the translation between ppdva and ppm per session
    calibration_params = calibration_data.dropna(subset=['session_id'], axis=0)
    calibration_params = calibration_params[calibration_params.trial_type == 'virtual-chinrest'].dropna(axis=1)

    session2ppdva = {}
    for session in np.unique(calibration_params.session_id):
        session2ppdva[session] = calibration_params[calibration_params.session_id == session]['px2deg'].values[-1]

    trial_data = perform_space_alignments(trial_data, ppdva=session2ppdva)

    long_df_cols = ['prolific_id', 'subject', 'session_id', 'study_id', 'choiceOrder',
                    'position_x_at_touch', 'position_y_at_touch', 'touch_x_to_center',
                    'touch_y_to_center', 'pos_x_touch_x_dist', 'pos_y_touch_y_dist',
                    'touch_x_to_center_dva', 'touch_y_to_center_dva', 'pos_x_touch_x_dist_dva',
                    'pos_y_touch_y_dist_dva', 'vector_touch_distance_dva', 'touch_deviation_angle']

    long_trial_df = transform_long_dataset(trial_data[trial_data.success == 1], long_df_cols)

    logger.info(f"The final trial data has the following columns: {trial_data.columns} and shape {trial_data.shape}")
    logger.info(f"The final trial data in long format contains only successful trials and has the following columns: "
                f"{long_trial_df.columns} and shape {long_trial_df.shape}")

    return calibration_data, training_data, main_session_data, trial_data, \
        question_data, calibration_params, long_trial_df


def ensure_formats(trial_data):
    """
    Transforms string representation of values into floats or lists
    Alternative: give load.json a type dictionary
    """
    # Time formats
    trial_data['animation_timestamps'] = helper.load_strings(trial_data.animation_timestamps,
                                                             trial_data.index, object)
    trial_data['touchOnTime'] = helper.load_strings(trial_data['touchOn'], trial_data.index, object)
    trial_data['touchOffTime'] = helper.load_strings(trial_data['touchOff'], trial_data.index, object)
    trial_data['flashOnTime'] = helper.load_strings(trial_data['flashOnTime'], trial_data.index, float)
    logger.info(f"In {sum(trial_data['flashOffTime'] == '[]')} "
                f"trials no flash offset was recorded. Dropping these trials.")
    trial_data = trial_data[trial_data['flashOffTime'] != '[]'].copy()
    trial_data.reset_index(drop=True)
    trial_data.loc[trial_data.index, 'flashOffTime'] = helper.load_strings(trial_data['flashOffTime'],

                                                                           trial_data.index, float)

    trial_data['scheduled_change_onset'] = helper.load_strings(trial_data.scheduled_change_onset,
                                                               trial_data.index, float)
    trial_data['scheduled_eventOnTime'] = trial_data['startTime'] + trial_data['scheduled_change_onset']
    trial_data['eventOnTime'] = trial_data['startTime'] + trial_data['flashOnTime']

    # space formats
    trial_data['touchX'] = helper.load_strings(trial_data.touchX, trial_data.index, object)
    trial_data['touchY'] = helper.load_strings(trial_data.touchY, trial_data.index, object)
    trial_data['position_x'] = helper.load_strings(trial_data.position_x, trial_data.index, object)
    trial_data['position_y'] = helper.load_strings(trial_data.position_y, trial_data.index, object)
    trial_data['shifted_position_x'] = helper.load_strings(trial_data.shifted_position_x, trial_data.index, object)
    trial_data['shifted_position_y'] = helper.load_strings(trial_data.shifted_position_y, trial_data.index, object)
    trial_data['choiceOrder'] = helper.load_strings(trial_data['choiceOrder'], trial_data.index, object)

    logger.info('Format conversions completed!')
    return trial_data


def perform_time_alignments(trial_data):
    """
    Aligns time columns first to trial onset, and then to flash onset
    """
    trial_data = align_columns_to_trial_on_time(trial_data)
    time_cols = ['trialOnTime_to_trialOnTime', 'startTime_to_trialOnTime', 'flashOnTime_aligned',
                 'flashOffTime_to_trialOnTime', 'endTime_to_trialOnTime', 'trialEndTime_to_trialOnTime',
                 'touchOnTime_to_trialOnTime',  'touchOffTime_to_trialOnTime']
    # change the name of the flash onset for better readability
    trial_data.rename(columns={'flashOnTime_to_trialOnTime': 'flashOnTime_aligned'}, inplace=True)
    logger.info('renamed flashOnTime_to_trialOnTime to flashOnTime_aligned')
    trial_data = align_columns_to_value(trial_data, time_cols, 'flashOnTime_aligned')
    trial_data = helper.align_to_multiple_values_filter_first(trial_data, 'animation_timestamps',  'touchOnTime')
    trial_data = helper.align_to_multiple_values_filter_first(trial_data, 'animation_timestamps',  'touchOffTime')
    # touch events relative to first touch
    onsets = trial_data['touchOnTime'].copy()
    first_onsets = [x[0] for x in onsets]
    trial_data['aligned_touchOn'] = [np.array(onsets.values[x]) - first_onsets[x] for x in range(len(first_onsets))]

    # time event/change to last interaction
    time_to_last_interaction = []

    for idx in trial_data.index:

        distances = trial_data.loc[idx, 'touchOnTime'] - trial_data.loc[idx, 'flashOnTime']
        distances = distances[distances < 0]
        time_to_last_interaction.append(max(distances))

    trial_data['interaction_to_change_distance'] = time_to_last_interaction

    return trial_data


def perform_space_alignments(trial_data, ppdva):
    """
    Align the position of the dots relative to

    """
    # get position at response time
    trial_data['position_x_at_touch'] = helper.get_position_at_response_time(trial_data, 'position_x',
                                                                             'shifted_position_x',
                                                                             'aligned_touchOn', 'eventOnTime')
    trial_data['position_y_at_touch'] = helper.get_position_at_response_time(trial_data, 'position_y',
                                                                             'shifted_position_y',
                                                                             'aligned_touchOn', 'eventOnTime')
    logger.info('extracted got positions at interaction times and created new columns')

    # align to screen center
    x_center = trial_data.windowWidth / 2
    y_center = trial_data.windowHeight / 2

    trial_data['touch_x_to_center'] = [trial_data['touchX'][x] - x_center[x]
                                       for x in trial_data.index]
    trial_data['touch_y_to_center'] = [trial_data['touchY'][x] - y_center[x]
                                       for x in trial_data.index]
    logger.info('Aligned touch responses to the screen center.')

    # distance between touch and position
    trial_data['pos_x_touch_x_dist'] = [helper.subtract_arrays_missing_values(trial_data['touch_x_to_center'][x],
                                                                              trial_data['position_x_at_touch'][x])
                                        for x in trial_data.index]
    trial_data['pos_y_touch_y_dist'] = [helper.subtract_arrays_missing_values(trial_data['touch_y_to_center'][x],
                                                                              trial_data['position_y_at_touch'][x])
                                        for x in trial_data.index]
    logger.info('computed the distance between touch response and location in pixel')

    # transform pixel to dva
    trial_data['px2dva'] = trial_data['session_id'].replace(ppdva)
    for col in ['touch_x_to_center', 'touch_y_to_center',
                'pos_x_touch_x_dist', 'pos_y_touch_y_dist']:
        trial_data[f'{col}_dva'] = trial_data[col] / trial_data.px2dva
    logger.info('expressed pixel values in dva')

    # get touch error as vector
    trial_data['vector_touch_distance_dva'] = [helper.pythagoras(trial_data.pos_x_touch_x_dist_dva[x],
                                               trial_data.pos_y_touch_y_dist_dva[x])
                                               for x in trial_data.index]
    logger.info('computed vector distance between touch position and point')

    # direction of the touch in dva
    trial_data['touch_deviation_angle'] = [helper.get_angles_from_list(trial_data['pos_x_touch_x_dist_dva'][x],
                                           trial_data['pos_y_touch_y_dist_dva'][x])
                                           for x in trial_data.index]
    logger.info('angle between touch position and point')

    return trial_data


def transform_long_dataset(wide_data, columns):
    """
    Transform a wide dataset to a long dataset
    """
    long_df = pd.DataFrame()
    for col in columns:
        first_entry_test = wide_data[col].iloc[0]
        if type(first_entry_test) == list or type(first_entry_test) == np.ndarray:
            if len(first_entry_test) == 6:
                long_df[col] = helper.get_long_column(wide_data, col)
                logger.info(f"stacked {col} into the long format dataset.")
            else:
                logger.info(f"{col} was a list of length {len(first_entry_test)}. \n "
                            f"The test entry was {first_entry_test}.")
        else:
            long_df[col] = helper.stack_unique_cols(wide_data, col, 6)
    return long_df


def align_columns_to_trial_on_time(trial_data):
    """
    Alignment to trial on time (first recorded timestamp from animation timestamps)
    Performs the extraction of trialOnTime and adds startTime to flashOnTime
    """
    trial_data['trialOnTime'] = [trial_data['animation_timestamps'][x][0] for x in trial_data.index]
    trial_data['flashOnTime'] += trial_data['startTime']
    trial_data['flashOffTime'] += trial_data['startTime']
    # set the end time of each trial to the maximum time people had to make the response
    trial_data['trialEndTime'] = trial_data['startTime'] + 1500
    logger.info('added start time to flash time (because flash time was reported relative to start time)')
    align_columns = ['trialOnTime', 'startTime', 'flashOnTime', 'flashOffTime',
                     'endTime', 'trialEndTime', 'touchOnTime', 'touchOffTime']
    trial_data = align_columns_to_value(trial_data, align_columns, 'trialOnTime')
    return trial_data


def align_columns_to_value(trial_data, col_list, value_col):
    """
    Performs subtraction of two columns for alignment.
    """
    for col in col_list:
        name = f"{col}_to_{value_col}"
        try:
            trial_data[name] = trial_data[col] - trial_data[value_col]
        except TypeError:
            # The column might be a list, so we convert it to a numpy array
            trial_data[name] = [np.array(trial_data[col][x]) - trial_data[value_col][x] for x in trial_data.index]
        logger.info(f'aligned the column {col} to {value_col}')
    return trial_data


def split_data(data):
    """
    Splits dataframe into subparts corresponding to the individual parts of the experiment
    Labels the condition in trial data
    """
    calibration_data = data[data.component == 'Calibrate_Screen'].copy()
    training_data = data[data.component == 'Training_Serial'].copy()
    main_session_data = data[data.component == 'Trials_Serial'].copy()
    trial_data = main_session_data[main_session_data.test_part == 'trial'].dropna(axis=1).copy()

    # add a column for conditions
    trial_data['condition'] = 'not defined'

    flash_data = trial_data[trial_data.flashShown == 1]
    no_flash_data = trial_data[trial_data.flashShown == 0]

    flash_shift_ids = flash_data[flash_data.stimJumped == 1].index
    flash_no_shift_ids = flash_data[flash_data.stimJumped == 0].index
    no_flash_shift_ids = no_flash_data[no_flash_data.stimJumped == 1].index
    no_flash_no_shift_ids = no_flash_data[no_flash_data.stimJumped == 0].index

    trial_data.loc[flash_shift_ids, 'condition'] = 'Flash_Shift'
    trial_data.loc[flash_no_shift_ids, 'condition'] = 'Flash_No_Shift'
    trial_data.loc[no_flash_shift_ids, 'condition'] = 'No_Flash_Shift'
    trial_data.loc[no_flash_no_shift_ids, 'condition'] = 'No_Flash_No_Shift'
    question_data = data[data.component == 'Outro_General'].copy()

    logger.info('datafile was split into the components of the experiment')
    return calibration_data, training_data, main_session_data, trial_data, question_data

