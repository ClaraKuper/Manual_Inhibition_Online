import json
import math
import numpy as np
import pandas as pd
from helper_funcs import causal_rate, align_to_start


class OneSubject:
    def __init__(self, prolific_id):
        self.prolific_id = prolific_id
        self.jatos_workers = None
        self.data = None
        self.data_flash_shift = None
        self.data_flash_noshift = None
        self.data_noflash_shift = None
        self.data_noflash_noshift = None
        self.sessions_completed = None
        self.calibration_data = None
        self.unsuccessful_trials = None
        self.trial_data = None
        self.questionnaire_data = None
        self.user_info = None
        self.platform = None
        self.device_width = None
        self.device_height = None
        self.n_trials_total = None
        self.n_trials_flash_shift = None
        self.n_trials_flash_noshift = None
        self.n_trials_noflash_shift = None
        self.n_trials_noflash_noshift = None

    def set_data(self, data):
        # add checks that the the prolific ID is in the data and that all columns are in the data
        self.data = data[data.prolific_id == self.prolific_id]

    def set_jatos_worker(self):
        self.jatos_workers = np.unique(self.data.subject)

    def set_calibration_data(self):
        calibration_data = self.data[self.data.component == 'Calibrate_Screen']
        calibration_data = calibration_data[calibration_data.trial_type == 'virtual-chinrest']
        self.calibration_data = calibration_data.dropna(axis=1)

    def set_trial_data(self, get_first):
        trial_data = self.data[self.data.component == 'Trials_Serial']
        trial_data = trial_data[trial_data.test_part == 'trial']
        if not get_first:
            self.unsuccessful_trials = trial_data[trial_data.success == 0].dropna(axis=1)
            self.trial_data = trial_data[trial_data.success == 1].dropna(axis=1)
        else:
            self.unsuccessful_trials = trial_data[200:].dropna(axis=1)
            self.trial_data = trial_data[0:200].dropna(axis=1)

        self.n_trials_total = len(self.trial_data)

    def set_questionnaire_data(self):
        self.questionnaire_data = self.data[self.data.component == 'Outro_General']

    def set_sessions_completed(self):
        self.sessions_completed = np.unique(self.questionnaire_data.session_number)

    def set_user_info(self):
        user_info = self.trial_data.userInfo
        unique_info = np.unique(user_info)
        try:
            assert (len(unique_info) == 1)
        except AssertionError:
            print(f"user {self.prolific_id} used {len(unique_info)} different devices")
        self.user_info = unique_info

    def set_platform(self):
        pass

    def set_device_width(self):
        window_width = self.trial_data.windowWidth
        unique_width = np.unique(window_width)
        try:
            assert (len(unique_width) == 1)
        except AssertionError:
            print(f"user {self.prolific_id} completed the experiment with {len(unique_width)} different widths")
        self.device_width = unique_width

    def set_device_height(self):
        window_height = self.trial_data.windowHeight
        unique_height = np.unique(window_height)
        try:
            assert (len(unique_height) == 1)
        except AssertionError:
            print(f"user {self.prolific_id} completed the experiment with {len(unique_height)} different heights")
        self.device_height = unique_height

    def set_trials_flash_shift(self):
        flash_data = self.trial_data[self.trial_data.flashShown == 1]
        flash_shift_data = flash_data[flash_data.stimJumped == 1]
        self.data_flash_shift = flash_shift_data
        self.n_trials_flash_shift = len(flash_shift_data)

    def set_trials_flash_noshift(self):
        flash_data = self.trial_data[self.trial_data.flashShown == 1]
        flash_noshift_data = flash_data[flash_data.stimJumped == 0]
        self.data_flash_noshift = flash_noshift_data
        self.n_trials_flash_noshift = len(flash_noshift_data)

    def set_trials_noflash_shift(self):
        noflash_data = self.trial_data[self.trial_data.flashShown == 0]
        noflash_shift_data = noflash_data[noflash_data.stimJumped == 1]
        self.data_noflash_shift = noflash_shift_data
        self.n_trials_noflash_shift = len(noflash_shift_data)

    def set_trials_noflash_noshift(self):
        noflash_data = self.trial_data[self.trial_data.flashShown == 0]
        noflash_noshift_data = noflash_data[noflash_data.stimJumped == 0]
        self.data_noflash_noshift = noflash_noshift_data
        self.n_trials_noflash_noshift = len(noflash_noshift_data)

    def set_all_properties(self, data, get_first=False):
        self.set_data(data)
        self.set_jatos_worker()
        self.set_calibration_data()
        self.set_trial_data(get_first)
        self.set_questionnaire_data()
        self.set_sessions_completed()
        self.set_user_info()
        self.set_platform()
        self.set_device_width()
        self.set_device_height()
        self.set_trials_flash_shift()
        self.set_trials_noflash_shift()
        self.set_trials_flash_noshift()
        self.set_trials_noflash_noshift()


class OneSubjectInhibition(OneSubject):
    def __init__(self, prolific_id):
        OneSubject.__init__(self, prolific_id)
        self.alpha = 1 / 50
        self.mask_cutoff = 20
        self.time_window_for_baseline = -100
        self.window_start = None
        self.window_end = None
        self.scale = None
        self.baseline = None
        self.onsets_combined = None
        self.onsets_flash_shift = None
        self.onsets_flash_noshift = None
        self.onsets_noflash_shift = None
        self.onsets_noflash_noshift = None
        self.rates_combined = None
        self.rates_flash_shift = None
        self.rates_noflash_noshift = None
        self.rates_flash_noshift = None
        self.rates_noflash_shift = None
        self.minimum_frequency_flash_shift = None
        self.minimum_frequency_flash_noshift = None
        self.minimum_frequency_noflash_shift = None
        self.minimum_frequency_noflash_noshift = None
        self.magnitude_flash_shift = None
        self.magnitude_flash_noshift = None
        self.magnitude_noflash_shift = None
        self.magnitude_noflash_noshift = None
        self.bottom_flash_shift = None
        self.bottom_flash_noshift = None
        self.bottom_noflash_shift = None
        self.bottom_noflash_noshift = None
        self.latency_flash_shift = None
        self.latency_flash_noshift = None
        self.latency_noflash_shift = None
        self.latency_noflash_noshift = None

    def set_window_scale(self):
        start_to_start = align_to_start(self.trial_data, 'startTime', 'startTime')
        start_to_flash = align_to_start(start_to_start, 'startTime_to_startTime', 'flashOnTime')
        end_to_start = align_to_start(self.trial_data, 'endTime', 'startTime')
        end_to_flash = align_to_start(end_to_start, 'endTime_to_startTime', 'flashOnTime')
        self.window_start = math.ceil(abs(min(start_to_flash.startTime_to_startTime_to_flashOnTime.values)))
        self.window_end = math.ceil(abs(max(end_to_flash.endTime_to_startTime_to_flashOnTime.values)))
        self.scale = np.arange(-1 * self.window_start, self.window_end, 1)

    def get_trials_per_window(self, data):
        start_to_start = align_to_start(data, 'startTime', 'startTime')
        start_to_flash = align_to_start(start_to_start, 'startTime_to_startTime', 'flashOnTime')
        end_to_start = align_to_start(data, 'endTime', 'startTime')
        end_to_flash = align_to_start(end_to_start, 'endTime_to_startTime', 'flashOnTime')
        trial_windows = []
        for i in data.index:
            trial_scale = np.arange(round(start_to_flash.startTime_to_startTime_to_flashOnTime[i][0]),
                                    round(end_to_flash.endTime_to_startTime_to_flashOnTime[i][0]), 1)
            trial_windows.append(trial_scale)
        trial_windows = np.concatenate(trial_windows).flatten()
        distribution, scale = np.histogram(trial_windows, bins=np.append(self.scale, self.scale[-1] + 1))
        distribution = [max(1, x) for x in distribution]
        return distribution

    def compute_onsets_flash_shift(self):
        onset_to_start = align_to_start(self.data_flash_shift, 'touchOn', 'startTime')
        onset_to_flash = align_to_start(onset_to_start, 'touchOn_to_startTime', 'flashOnTime')
        onset_list = np.concatenate(onset_to_flash.touchOn_to_startTime_to_flashOnTime.values).flatten()
        self.onsets_flash_shift = onset_list

    def compute_onsets_flash_noshift(self):
        onset_to_start = align_to_start(self.data_flash_noshift, 'touchOn', 'startTime')
        onset_to_flash = align_to_start(onset_to_start, 'touchOn_to_startTime', 'flashOnTime')
        onset_list = np.concatenate(onset_to_flash.touchOn_to_startTime_to_flashOnTime.values).flatten()
        self.onsets_flash_noshift = onset_list

    def compute_onsets_noflash_shift(self):
        onset_to_start = align_to_start(self.data_noflash_shift, 'touchOn', 'startTime')
        onset_to_flash = align_to_start(onset_to_start, 'touchOn_to_startTime', 'flashOnTime')
        onset_list = np.concatenate(onset_to_flash.touchOn_to_startTime_to_flashOnTime.values).flatten()
        self.onsets_noflash_shift = onset_list

    def compute_onsets_noflash_noshift(self):
        onset_to_start = align_to_start(self.data_noflash_noshift, 'touchOn', 'startTime')
        onset_to_flash = align_to_start(onset_to_start, 'touchOn_to_startTime', 'flashOnTime')
        onset_list = np.concatenate(onset_to_flash.touchOn_to_startTime_to_flashOnTime.values).flatten()
        self.onsets_noflash_noshift = onset_list

    def compute_rate_flash_shift(self, normalize=True):
        self.n_trials_flash_shift = self.get_trials_per_window(self.data_flash_shift)
        if normalize:
            n_trials = self.n_trials_flash_shift
        else:
            n_trials = len(self.data_flash_shift)
        rate, scale = causal_rate(self.onsets_flash_shift, self.window_start, self.window_end,
                                  n_trials, alpha=self.alpha)
        rate = np.multiply(rate, np.array(self.n_trials_flash_shift) > self.mask_cutoff)
        self.rates_flash_shift = rate

    def compute_rate_flash_noshift(self, normalize=True):
        self.n_trials_flash_noshift = self.get_trials_per_window(self.data_flash_noshift)
        if normalize:
            n_trials = self.n_trials_flash_noshift
        else:
            n_trials = len(self.data_flash_noshift)
        rate, scale = causal_rate(self.onsets_flash_noshift, self.window_start, self.window_end,
                                  n_trials, alpha=self.alpha)
        rate = np.multiply(rate, np.array(self.n_trials_flash_noshift) > self.mask_cutoff)
        self.rates_flash_noshift = rate

    def compute_rate_noflash_shift(self, normalize=True):
        self.n_trials_noflash_shift = self.get_trials_per_window(self.data_noflash_shift)
        if normalize:
            n_trials = self.n_trials_noflash_shift
        else:
            n_trials = len(self.data_noflash_shift)
        rate, scale = causal_rate(self.onsets_noflash_shift, self.window_start, self.window_end,
                                  n_trials, alpha=self.alpha)
        rate = np.multiply(rate, np.array(self.n_trials_noflash_shift) > self.mask_cutoff)
        self.rates_noflash_shift = rate

    def compute_rate_noflash_noshift(self, normalize=True):
        self.n_trials_noflash_noshift = self.get_trials_per_window(self.data_noflash_noshift)
        if normalize:
            n_trials = self.n_trials_noflash_noshift
        else:
            n_trials = len(self.data_noflash_noshift)
        rate, scale = causal_rate(self.onsets_noflash_noshift, self.window_start, self.window_end,
                                  n_trials, alpha=self.alpha)
        rate = np.multiply(rate, np.array(self.n_trials_noflash_noshift) > self.mask_cutoff)
        self.rates_noflash_noshift = rate

    def compute_onsets_combined(self):
        onset_to_start = align_to_start(self.trial_data, 'touchOn', 'startTime')
        onset_to_flash = align_to_start(onset_to_start, 'touchOn_to_startTime', 'flashOnTime')
        onset_list = np.concatenate(onset_to_flash.touchOn_to_startTime_to_flashOnTime.values).flatten()
        self.onsets_combined = onset_list

    def compute_rate_combined(self):
        self.n_trials_total = self.get_trials_per_window(self.trial_data)
        rate, scale = causal_rate(self.onsets_combined, self.window_start, self.window_end,
                                  self.n_trials_total, alpha=self.alpha)
        rate = np.multiply(rate, np.array(self.n_trials_total) > self.mask_cutoff)
        self.rates_combined = rate

    def compute_baseline(self):
        indexes_upper = np.where(0 > self.scale)
        indexes_lower = np.where(self.scale > self.time_window_for_baseline)
        indexes = np.intersect1d(indexes_lower, indexes_upper)
        self.baseline = np.mean(self.rates_combined[indexes])

    def set_all_onsets(self):
        self.compute_onsets_combined()
        self.compute_onsets_flash_shift()
        self.compute_onsets_flash_noshift()
        self.compute_onsets_noflash_shift()
        self.compute_onsets_noflash_noshift()

    def compute_all_rates(self, normalize=True):
        self.set_window_scale()
        self.compute_rate_combined()
        self.compute_rate_flash_shift(normalize)
        self.compute_rate_flash_noshift(normalize)
        self.compute_rate_noflash_shift(normalize)
        self.compute_rate_noflash_noshift(normalize)

    def normalize_rates(self):
        self.compute_baseline()
        self.rates_flash_shift = self.rates_flash_shift / self.baseline
        self.rates_flash_noshift = self.rates_flash_noshift / self.baseline
        self.rates_noflash_shift = self.rates_noflash_shift / self.baseline
        self.rates_noflash_noshift = self.rates_noflash_noshift / self.baseline

    def get_minimum(self):
        indexes_1 = np.where(self.scale > 0)
        indexes_2 = np.where(np.array(self.n_trials_flash_shift) > self.mask_cutoff)
        self.minimum_frequency_flash_shift = np.min(self.rates_flash_shift[np.intersect1d(indexes_1, indexes_2)])
        indexes_2 = np.where(np.array(self.n_trials_flash_noshift) > self.mask_cutoff)
        self.minimum_frequency_flash_noshift = np.min(self.rates_flash_noshift[np.intersect1d(indexes_1, indexes_2)])
        indexes_2 = np.where(np.array(self.n_trials_noflash_shift) > self.mask_cutoff)
        self.minimum_frequency_noflash_shift = np.min(self.rates_noflash_shift[np.intersect1d(indexes_1, indexes_2)])
        indexes_2 = np.where(np.array(self.n_trials_noflash_noshift) > self.mask_cutoff)
        self.minimum_frequency_noflash_noshift = np.min(
            self.rates_noflash_noshift[np.intersect1d(indexes_1, indexes_2)])

    def get_magnitude(self):
        self.magnitude_flash_shift = abs(1 - self.minimum_frequency_flash_shift)
        self.magnitude_flash_noshift = abs(1 - self.minimum_frequency_flash_noshift)
        self.magnitude_noflash_shift = abs(1 - self.minimum_frequency_noflash_shift)
        self.magnitude_noflash_noshift = abs(1 - self.minimum_frequency_noflash_noshift)

    def get_bottom_of_dip(self):
        """bottom of the dip was defined as the period at which microsaccade frequency was below the
        minimum plus 10 % of the difference between 1(the baseline) and the minimum frequency"""
        bottom_flash_shift = np.where(self.rates_flash_shift < self.minimum_frequency_flash_shift + 0.1)
        self.bottom_flash_shift = np.intersect1d(bottom_flash_shift, np.where(self.rates_flash_shift > 0))
        bottom_flash_noshift = np.where(self.rates_flash_noshift < self.minimum_frequency_flash_noshift + 0.1)
        self.bottom_flash_noshift = np.intersect1d(bottom_flash_noshift, np.where(self.rates_flash_noshift > 0))
        bottom_noflash_shift = np.where(self.rates_noflash_shift < self.minimum_frequency_noflash_shift + 0.1)
        self.bottom_noflash_shift = np.intersect1d(bottom_noflash_shift, np.where(self.rates_noflash_shift > 0))
        bottom_noflash_noshift = np.where(self.rates_noflash_noshift < self.minimum_frequency_noflash_noshift + 0.1)
        self.bottom_noflash_noshift = np.intersect1d(bottom_noflash_noshift, np.where(self.rates_noflash_noshift > 0))

    def get_latency(self):
        """latency is the time point of the minimum - change this later!"""
        self.latency_flash_shift = self.scale[np.where(
            self.rates_flash_shift == self.minimum_frequency_flash_shift)]
        self.latency_flash_noshift = self.scale[np.where(
            self.rates_flash_noshift == self.minimum_frequency_flash_noshift)]
        self.latency_noflash_shift = self.scale[np.where(
            self.rates_noflash_shift == self.minimum_frequency_noflash_shift)]
        self.latency_noflash_noshift = self.scale[np.where(
            self.rates_noflash_noshift == self.minimum_frequency_noflash_noshift)]

    def compute_metrics(self):
        self.get_minimum()
        self.get_magnitude()
        self.get_bottom_of_dip()
        self.get_latency()


def compute_distance_pythagoras(x1, x2, y1, y2):
    return np.sqrt(((x1 - x2) ** 2) + ((y1 - y2) ** 2))


def smooth_array(array, time_array, smooth_before, smooth_after, time):
    start = time - smooth_before
    end = time + smooth_after
    idx_1 = np.where(time_array >= start)
    idx_2 = np.where(time_array < end)
    return np.mean(array[np.intersect1d(idx_1, idx_2)])


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
