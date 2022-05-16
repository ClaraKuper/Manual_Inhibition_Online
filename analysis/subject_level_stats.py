import helper_funcs as helper
import json
import math
import numpy as np
import pandas as pd

# Todo restructure
# Todo add logging


class OneSubject:
    def __init__(self, prolific_id):
        self.prolific_id = prolific_id
        self.jatos_workers = None
        self.data = None
        self.sessions_completed = None
        self.calibration_data = None
        self.unsuccessful_trials = None
        self.trial_data = None
        self.preprocessed_trial_data = None
        self.first_trial_data = None
        self.last_trial_data = None
        self.questionnaire_data = None
        self.user_info = None
        self.device_width = None
        self.device_height = None
        self.n_trials = None

    def set_all_properties(self, data, preprocessed_trial_data):
        self._set_data(data)
        self._set_jatos_worker()
        self._set_calibration_data()
        self._set_trial_data(preprocessed_trial_data)
        self._set_questionnaire_data()
        self._set_sessions_completed()
        self._set_user_info()
        self._set_device_size()

    def _set_data(self, data):
        """
        Filters the dataframe to include only data from the prolific id of the subject
        data: pd dataframe, contains at least the column "prolific_id"
        """
        # add checks that the the prolific ID is in the data and that all columns are in the data
        self.data = data[data.prolific_id == self.prolific_id]

    def _set_jatos_worker(self):
        self.jatos_workers = np.unique(self.data.subject)

    def _set_calibration_data(self):
        """
        Filters full data frame to trials from the calibration part.
        """
        calibration_data = self.data[self.data.component == 'Calibrate_Screen']
        calibration_data = calibration_data[calibration_data.trial_type == 'virtual-chinrest']
        self.calibration_data = calibration_data.dropna(axis=1)

    def _set_trial_data(self, preprocessed_data):
        """
        Filters full data frame to trials from the core experiment. Successful and unsuccessful trials will be saved,
        as well as the first 200 and the trailing trials.
        """
        trial_data = self.data[self.data.component == 'Trials_Serial']
        trial_data = trial_data[trial_data.test_part == 'trial']
        helper.convert_string_to_array(trial_data)
        # add column with start time
        self.unsuccessful_trials = trial_data[trial_data.success == 0].dropna(axis=1)
        self.trial_data = trial_data[trial_data.success == 1].dropna(axis=1)
        self.first_trial_data = trial_data[0:200].dropna(axis=1)
        self.last_trial_data = trial_data[200:].dropna(axis=1)
        self.preprocessed_trial_data = preprocessed_data[preprocessed_data.prolific_id == self.prolific_id]

    def _set_questionnaire_data(self):
        self.questionnaire_data = self.data[self.data.component == 'Outro_General']

    def _set_sessions_completed(self):
        self.sessions_completed = np.unique(self.questionnaire_data.session_number)

    def _set_user_info(self):
        """
        Filter information about the used browser and phone type
        """
        user_info = self.trial_data.userInfo
        unique_info = np.unique(user_info)
        try:
            assert (len(unique_info) == 1)
        except AssertionError:
            print(f"user {self.prolific_id} used {len(unique_info)} different devices")
        self.user_info = unique_info

    def _set_device_size(self):
        self.device_width = self._get_device_property('windowWidth')
        self.device_height = self._get_device_property('windowHeight')

    def _get_device_property(self, column):
        window_prop = self.trial_data[column]
        unique_prop = np.unique(window_prop)
        try:
            assert (len(unique_prop) == 1)
        except AssertionError:
            print(f"user {self.prolific_id} completed the experiment with {len(unique_prop)} different "
                  f"values for {column}")
        return unique_prop


empty_property_array = {'all': [],
                        'flash': [],
                        'no_flash': [],
                        'shift': [],
                        'no_shift': [],
                        'flash_shift': [],
                        'flash_no_shift': [],
                        'no_flash_shift': [],
                        'no_flash_no_shift': []}


class OneSubjectInhibition(OneSubject):
    def __init__(self, prolific_id, parameter_dict):
        OneSubject.__init__(self, prolific_id)
        self.alpha = parameter_dict['alpha'] or 1 / 50
        self.minimum_n_cutoff = parameter_dict['minimum_n_cutoff'] or 20
        self.time_window_for_baseline = parameter_dict['time_window_for_baseline'] or -100
        self.window_start = parameter_dict['window_start'] or 1000
        self.window_end = parameter_dict['window_end'] or 2000
        # todo: create analysis classes
        self.scale = np.arange(-1 * self.window_start, self.window_end, 1)
        self.n_trials = empty_property_array.copy()
        self.n_trials_per_window = empty_property_array.copy()
        self.onsets = empty_property_array.copy()
        self.rates = empty_property_array.copy()
        self.normalized_baseline_rates = empty_property_array.copy()
        self.normalized_null_condition_rates = empty_property_array.copy()
        self.metrics_search_start = np.where(self.scale == parameter_dict['metrics_search_start'])[0]
        self.metrics_search_end = np.where(self.scale == parameter_dict['metrics_search_end'])[0]
        self.metrics = pd.DataFrame(columns=['flashShown', 'stimJumped', 'minimum',
                                             'magnitude', 'bottom', 'latency'])

    def run_rate_pipeline(self, mask_rate=True, normalization='per_window'):
        flash_conditions = [None, 0, 1]
        jump_conditions = [None, 0, 1]
        for flash in flash_conditions:
            for jump in jump_conditions:

                data, name = filter_by_conditions(self.preprocessed_trial_data, {'flashShown': flash,
                                                                                 'stimJumped': jump})
                # number of trials
                self.n_trials[name] = len(data)
                # onsets
                self.compute_onsets(data, name)
                # trials
                self.get_trials_per_window(data, name)
                # rates
                self.compute_rates(name, mask_rate=mask_rate, normalization=normalization)
                # normalized baseline rates
                baseline = compute_baseline(self.scale, self.time_window_for_baseline, self.rates[name])
                self.normalized_baseline_rates[name] = self.rates[name]/baseline

    def normalize_to_null_condition(self, null_condition):
        for key in self.rates.keys():
            self.normalized_null_condition_rates[key] = normalize_rates_to_null_condition(
                self.rates[key],
                self.rates[null_condition].copy()
            )

    def run_metrics_pipeline(self, normalization='null_condition'):
        if normalization == 'null_condition':
            data = self.normalized_null_condition_rates
        elif normalization == 'baseline':
            data = self.normalized_baseline_rates
        elif normalization == 'none':
            data = self.rates
        else:
            raise ValueError(f'The normalization argument {normalization} is not known. '
                             f'Please use "null_condition" (default), "baseline", "none"')

        for key in data.keys():
            metric_frame = pd.DataFrame(columns=['flashShown', 'stimJumped', 'minimum',
                                                 'magnitude', 'bottom', 'latency'])
            metric_frame.loc[0, 'flashShown'] = int('no_flash' not in key)
            metric_frame.loc[0, 'stimJumped'] = int('no_shift' not in key)

            metric_search_data = np.array(data[key])[self.metrics_search_start[0]:self.metrics_search_end[0]]
            metric_frame.loc[0, 'minimum'] = np.min(metric_search_data)
            # TODO Make this robust to different normalizations
            metric_frame.loc[0, 'magnitude'] = 1 - metric_frame.loc[0, 'minimum']
            metric_frame.loc[0, 'bottom'] = get_bottom_of_dip(
                metric_search_data, metric_frame.loc[0, 'minimum']
            )
            try:
                metric_frame.loc[0, 'latency'] = get_latency(
                    metric_search_data,
                    np.array(self.scale)[self.metrics_search_start[0]:self.metrics_search_end[0]],
                    metric_frame.loc[0, 'minimum'])
            except NotImplementedError:
                print('missing latency')
            self.metrics = pd.concat([self.metrics, metric_frame], ignore_index=True)

    def compute_onsets(self, data, condition_name):
        """
        Concatenate touch onset times relative to flash and assigns onset value
        """
        # get data
        onset_list = np.concatenate(data['touchOnTime_to_trialOnTime_to_flashOnTime_aligned'].values)
        onset_list = onset_list.flatten()
        self.onsets[condition_name] = onset_list

    def compute_rates(self, condition_name, mask_rate, normalization='per_window'):
        """
        Compute movement rates based on touch onset times
        """
        if normalization == 'per_window':
            n_trials = self.n_trials_per_window[condition_name]
        elif normalization == 'uniform':
            n_trials = self.n_trials[condition_name]
        else:
            raise ValueError('Unknown normalization argument. '
                             'Use "per_window" or "uniform"')

        rate, scale = helper.causal_rate(self.onsets[condition_name], self.window_start, self.window_end,
                                         n_trials, alpha=self.alpha)
        if mask_rate:
            rate = np.multiply(rate, np.array(self.n_trials[condition_name]) > self.minimum_n_cutoff)
        self.rates[condition_name] = rate

    def get_trials_per_window(self, data, name):

        trial_windows = []
        for i in data.index:
            trial_scale = np.arange(round(self.preprocessed_trial_data[
                                              'trialOnTime_to_trialOnTime_to_flashOnTime_aligned'][i]),
                                    round(self.preprocessed_trial_data[
                                              'trialEndTime_to_trialOnTime_to_flashOnTime_aligned'][i]), 1)
            trial_windows.append(trial_scale)
        trial_windows = np.concatenate(trial_windows).flatten()
        distribution, scale = np.histogram(trial_windows, bins=np.append(self.scale, self.scale[-1] + 1))
        distribution = [max(1, x) for x in distribution]

        self.n_trials_per_window[name] = distribution


def filter_by_conditions(data, kwargs):
    flash_name = ''
    shift_name = ''
    if not kwargs['flashShown'] is None:
        data = data[data['flashShown'] == kwargs['flashShown']]
        flash_name = ['no_flash', 'flash'][kwargs['flashShown']]
    if not kwargs['stimJumped'] is None:
        data = data[data['stimJumped'] == kwargs['stimJumped']]
        shift_name = ['no_shift', 'shift'][kwargs['stimJumped']]

    # determine the condition name
    if flash_name == '' or shift_name == '':
        name = flash_name+shift_name
    else:
        name = f'{flash_name}_{shift_name}'
    if name == '':
        name = 'all'

    return data, name


def compute_baseline(scale, time_window_for_baseline, rates):
    indexes_upper = np.where(0 > scale)
    indexes_lower = np.where(scale > time_window_for_baseline)
    indexes = np.intersect1d(indexes_lower, indexes_upper)
    return np.mean(rates[indexes])


def normalize_rates_to_null_condition(rates, null_rates):
    # avoid 0-division
    null_rates[null_rates <= 1] = 1
    # divide
    return rates/null_rates


def get_latency(data, time_scale, minimum):
    """latency is the time point of the minimum"""
    return time_scale[np.where(data == minimum)[0][0]]


def get_bottom_of_dip(rates, minimum_frequency, baseline=1):
    """bottom of the dip was defined as the period at which microsaccade frequency was below the
    minimum plus 10 % of the difference between the baseline and the minimum frequency"""
    tolerance = (baseline - minimum_frequency) * 0.1
    bottom = np.where(rates < minimum_frequency + tolerance)
    return len(bottom[0])

##########################################################
# TODO: Later ############################################
##########################################################


class OneSubjectErrorSize(OneSubject):
    def __init__(self, prolific_id, data):
        OneSubject.__init__(self, prolific_id)
        self.set_all_properties(data)
        self.baseline = None
        self.smooth = 40
        self.flash_shift = None
        self.flash_noshift = None
        self.noflash_shift = None
        self.noflash_noshift = None

    def get_distance_to_dot(self, dot_x, dot_y, colname):
        distance = []
        for i in self.trial_data.index:
            touch_x = json.loads(self.trial_data.loc[i, 'touchX'])
            touch_y = json.loads(self.trial_data.loc[i, 'touchY'])
            position_x = json.loads(self.trial_data.loc[i, dot_x])
            position_y = json.loads(self.trial_data.loc[i, dot_y])
            width = self.trial_data.loc[i, 'windowWidth']/2
            height = self.trial_data.loc[i, 'windowHeight']/2

            dist = [compute_distance_pythagoras(
                touch_x[x], position_x[x] + width, touch_y[x], position_y[x] + height
            ) for x in range(len(touch_x))]
            distance.append(dist)

        self.trial_data[colname] = distance

    def get_distance_to_event(self):
        onset_to_start = align_to_start(self.trial_data, 'touchOn', 'startTime')
        onset_to_flash = align_to_start(onset_to_start, 'touchOn_to_startTime', 'flashOnTime')

        self.trial_data['distance_to_onset'] = onset_to_flash.touchOn_to_startTime_to_flashOnTime

    def parse_conditions(self):
        flash_data = self.trial_data[self.trial_data.flashShown == 1]
        noflash_data = self.trial_data[self.trial_data.flashShown == 0]

        self.flash_shift = flash_data[flash_data.stimJumped == 1].reset_index(drop=True)
        self.flash_noshift = flash_data[flash_data.stimJumped == 0].reset_index(drop=True)
        self.noflash_shift = noflash_data[noflash_data.stimJumped == 1].reset_index(drop=True)
        self.noflash_noshift = noflash_data[noflash_data.stimJumped == 0].reset_index(drop=True)

        self.baseline = np.mean(np.concatenate(self.noflash_noshift.distance_original).flatten())

    def compute_moving_average_error(self, data):
        distance_original = np.concatenate(data.distance_original).flatten()
        distance_shifted = np.concatenate(data.distance_shifted).flatten()
        time = np.concatenate(data.distance_to_onset).flatten()

        # sort all arrays by time
        idx = time.argsort()
        distance_original = distance_original[idx]
        distance_shifted = distance_shifted[idx]
        time = time[idx]

        distance_original_smooth = [smooth_array(
            distance_original, time, self.smooth, self.smooth, i
        ) for i in np.arange(-500, 1000, 1)]

        distance_shifted_smooth = [smooth_array(
            distance_shifted, time, self.smooth, self.smooth, i
        ) for i in np.arange(-500, 1000, 1)]

        return distance_original_smooth, distance_shifted_smooth, np.arange(-500, 1000, 1)


def assert_condition(condition, function):
    try:
        assert condition
    except AssertionError:
        print(f'Assertion check failed. Executing alternative function instead.')
        function()
