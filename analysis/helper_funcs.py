import json
import numpy as np
import pandas as pd


def clean_dataframe(data):
    data = data.copy()
    # take only trial rows
    data = data.drop(np.where(data.test_part != 'trial')[0]).reset_index(drop=True)
    # take only success rows
    data = data.drop(np.where(data.success != 1.0)[0]).reset_index(drop=True)
    # return
    return data


def align_times(data, column, start_column):
    data = data.copy()
    aligned_list = []
    colname = "{}_to_{}".format(column, start_column)

    for idx in data.index:
        try:
            aligned_values = data.loc[idx, column] - data.loc[idx, start_column]
        except Exception as e:
            try:
                unaligned_values = json.loads(data.loc[idx, column])
                align_to_values = data.loc[idx, start_column]
                aligned_values = unaligned_values - align_to_values
            except Exception as e:
                unaligned_values = data.loc[idx, column]
                align_to_values = json.loads(data.loc[idx, start_column])
                aligned_values = unaligned_values - align_to_values

        aligned_list.append(aligned_values)

    data[colname] = aligned_list

    return data


def align_to_multiple_values(data, column, multi_value_column):
    aligned_list = []
    colname = "{}_to_{}".format(column, multi_value_column)
    for idx in data.index:
        index_list = []
        for value in data.loc[idx, multi_value_column]:
            aligned_values = [x - value for x in data.loc[idx, column]]
            index_list.append(aligned_values)
        try:
            index_list = np.concatenate(index_list)
        except:
            pass
        aligned_list.append(index_list)
    data[colname] = aligned_list

    return data


def causal_rate(move_onset, lock_window_start, lock_window_end, n_trials, alpha=1 / 50):
    """

     analyse rate in causal time window

     input:    move_onset  - movement onset times
               lock_window_start  - window before lock
               lock_window_end  - window after lock
               n_trials      - number of trials

     output:   rate    - movement rate
               scale   - time axis

    12.12.2005 by Martin Rolfs
    21.06.2021 translated to python by Clara Kuper
    """
    scale = np.arange(-lock_window_start, lock_window_end, 1)
    # check how many trials these values came from
    if type(n_trials) == int:
        n_trials = np.linspace(n_trials, n_trials, len(scale))
    elif len(n_trials) != len(scale):
        raise ValueError('n_trials must have the same as the length of -lock_window_start:lock_window_end!'
                         f'But has length {len(n_trials)} instead of {len(scale)}')
    # alpha defines how much the distribution is shifted
    alpha = alpha
    # define empty arrays for scale and rate
    rate = []


    # loop through all time windows
    for idx, t in enumerate(scale):
        # compute tau
        tau = t - move_onset + 1 / alpha
        # filter tau as event 0/1
        tau = tau[tau > 0]
        # get the number of saccades in a given window
        causal = alpha ** 2 * tau * np.exp(-alpha * tau)
        # save the rate
        rate.append(sum(causal) * 1000 / n_trials[idx])

    return rate, scale


def load_strings(col, index, dtype):
    collected_array = np.array([json.loads(col[x]) for x in index], copy=False, dtype=dtype)
    if dtype == object:
        try:
            collected_array = [x.tolist() for x in collected_array]
        except AttributeError:
            pass
    return collected_array


def convert_string_to_array(trial_data):
    """
    Interative and hard-coded translation of string-based columns to numpy arrays
    :param trial_data: the trial data frame from my manual inhibition experiment
    :return: None
    """
    trial_data['animation_timestamps_list'] = load_strings(trial_data.animation_timestamps, trial_data.index, object)
    trial_data['touchOn_list'] = load_strings(trial_data.touchOn, trial_data.index, object)
    trial_data['touchOff_list'] = load_strings(trial_data.touchOff, trial_data.index, object)
    trial_data['scheduled_eventOn_float'] = load_strings(trial_data.scheduled_change_onset, trial_data.index, float)
    trial_data['eventOn_float'] = load_strings(trial_data.flashOnTime, trial_data.index, float)
    trial_data['touchX_list'] = load_strings(trial_data.touchX, trial_data.index, object)
    trial_data['touchY_list'] = load_strings(trial_data.touchY, trial_data.index, object)
    trial_data['position_x_list'] = load_strings(trial_data.position_x, trial_data.index, object)
    trial_data['position_y_list'] = load_strings(trial_data.position_y, trial_data.index, object)
    trial_data['shifted_position_x_list'] = load_strings(trial_data.shifted_position_x, trial_data.index, object)
    trial_data['shifted_position_y_list'] = load_strings(trial_data.shifted_position_y, trial_data.index, object)


def align_to_multiple_values_filter_first(data, column, multi_value_column):
    aligned_list = []
    colname = "{}_to_{}".format(column, multi_value_column)
    for idx in data.index:
        index_list = []
        for value in data.loc[idx, multi_value_column]:
            aligned_values = [x - value for x in data.loc[idx, column]]
            aligned_values = np.array(aligned_values)
            aligned_values = aligned_values[aligned_values >= 0]
            try:
                index_list.append(min(aligned_values))
            except ValueError:
                pass
        try:
            index_list = np.concatenate(index_list)
        except:
            pass
        aligned_list.append(index_list)
    data[colname] = aligned_list

    return data


def get_position_at_response_time(data, start_position_col, shift_position_col, response_time_col, change_time_col):
    pos_at_touch = []

    for idx in data.index:
        touch_on = data[response_time_col][idx]
        change_on = data[change_time_col][idx]
        pos_before = data[start_position_col][idx]
        pos_after = data[shift_position_col][idx]
        if len(touch_on) < len(pos_before):
            # not enough touches
            pos_before = pos_before[:len(touch_on)]
            pos_after = pos_after[:len(touch_on)]
        elif len(touch_on) > len(pos_before):
            # too many touches
            touch_on = touch_on[:len(pos_before)]

        mask_before = touch_on <= change_on
        masked_positions_before = np.array(pos_before)[mask_before]
        masked_positions_after = np.array(pos_after)[np.where(mask_before == False)]
        masked_positions = np.concatenate([masked_positions_before, masked_positions_after])

        pos_at_touch.append(masked_positions.tolist())

    return pos_at_touch


def subtract_arrays_missing_values(array_a, array_b):
    try:
        result = array_a - array_b
    except ValueError:
        if len(array_a) > len(array_b):
            result = array_a[:len(array_b)] - array_b
        else:
            result = array_a - array_b[:len(array_a)]
    return result


def compute_distance_pythagoras(x1, x2, y1, y2):
    x_val = x1 - x2
    y_val = y1 - y2

    return pythagoras(x_val, y_val)


def pythagoras(x_value, y_value):
    """
    takes two values and computes the hypothenuse between them
    """
    return np.sqrt(x_value**2 + y_value**2)


def cart2pol(x, y):
    radius = np.sqrt(x**2 + y**2)
    theta_rad = np.arctan2(y, x)
    if theta_rad < 0:
        theta_rad += 2 * np.pi
    theta_dva = theta_rad * (180/np.pi)
    return radius, theta_rad, theta_dva


def pol2cart(radius, theta):
    x = radius * np.cos(theta)
    y = radius * np.sin(theta)
    return x, y


def get_angles_from_list(x_distance, y_distance):
    return [cart2pol(x_distance[x], y_distance[x])[2] for x in range(len(x_distance))]


def calibration_valid(params):
    return params.win_width_deg >= 17 and 200 <= params.view_dist_mm <= 600


def get_long_column(data, col_name):
    wide_format = pd.DataFrame(data[col_name].values.tolist())
    long_format = wide_format.stack()

    return long_format.reset_index()[0].values


def stack_unique_cols(data, col_name, n_stack):
    stack_df = pd.DataFrame()

    for s in range(n_stack):
        stack_df[s] = data[col_name]

    return stack_df.stack().reset_index()[0].values


def smooth_array(array, time_array, smooth_before, smooth_after, time):
    start = time - smooth_before
    end = time + smooth_after
    idx_1 = np.where(time_array >= start)
    idx_2 = np.where(time_array < end)
    return np.mean(array[np.intersect1d(idx_1, idx_2)])