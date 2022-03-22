/* create timeline */
let timeline = []; // timeline to run on jsPsych.init

let repeat_IDs = []; // a list of all IDs that have to be repeated
let repeat_trials = []; // gets assigned to repeat_IDs at the end of each run
let first_set = true;
let T; // initialize value for trial parameters
let id_redirect_to = {
    '1':'https://app.prolific.co/submissions/complete?cc=3350BEDA',
    '2':'https://app.prolific.co/submissions/complete?cc=3350BEDA',
    '3':'https://app.prolific.co/submissions/complete?cc=3350BEDA',
    '4':'https://app.prolific.co/submissions/complete?cc=3350BEDA',
}

// boolean checks
let calibrationValid; // do the calibration parameters make sense
let correctPassword; // did the participant tell us the correct password?
let consentParticipation; //
let consentProcessing; //
let lateResponse; // was the response given in time
let earlyResponse; // was the response given too early
let tooManyTouches; // too many interactions with the screen were registered
let repeat; // check if the current trial should be repeated or not
let screenInLandscape; // check how often the Display was rotated
let orderResponse; // check if all buttons in the serial trial were pressed in order
let nTrials_executed = 0; // just a counter to see how many trials were executed

