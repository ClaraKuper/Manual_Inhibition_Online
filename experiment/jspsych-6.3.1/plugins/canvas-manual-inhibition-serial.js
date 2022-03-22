/*
 * Plugin for drawing dots on a canvas
 * By Clara Kuper, 2022
 */

jsPsych.plugins["canvas-mi-serial"] = (function () {

    let plugin = {};

    plugin.info = {
        name: "canvas-mi-serial",
        parameters: {
            flash_color: {
                type: jsPsych.plugins.parameterType.STRING, // BOOL, STRING, INT, FLOAT, FUNCTION, KEYCODE, SELECT, HTML_STRING, IMAGE, AUDIO, VIDEO, OBJECT, COMPLEX
                default: '#FFFFFF',
                description: "The color of the flash in the upper and lower part of the screen"
            },
            target_pos_x: {
                type: jsPsych.plugins.parameterType.INT,
                default: undefined,
                description: "The x position of the dots in the beginning"
            },
            target_pos_y: {
                type: jsPsych.plugins.parameterType.INT,
                default: undefined,
                description: "The y position of the dots in the beginning"
            },
            shifted_target_pos_x: {
                type: jsPsych.plugins.parameterType.INT,
                default: undefined,
                description: "The x position of the array after the shift"
            },
            shifted_target_pos_y: {
                type: jsPsych.plugins.parameterType.INT,
                default: undefined,
                description: "The y position of the array after the shift"
            },
            flash_duration: {
                type: jsPsych.plugins.parameterType.INT,
                default: 30,
                description: 'How long the flash is visible'
            },
            change_onset: {
                type: jsPsych.plugins.parameterType.INT,
                default: 500,
                description: 'How long the flash is visible'
            },
            trial_duration: {
                type: jsPsych.plugins.parameterType.INT,
                default: 1000,
                description: 'How long the task is run before timeout'
            },
            wait_after: {
                type: jsPsych.plugins.parameterType.INT,
                default: 500,
                description: "waiting time before we close the trial"
            },
            circle_color: {
                type: jsPsych.plugins.parameterType.STRING,
                default: '#000000',
                description: "default color of all circles"
            },
            circle_radius: {
                type: jsPsych.plugins.parameterType.INT,
                default: 0.5,
                description: 'The size of each individual dot.',
            },
            background_color: {
                type: jsPsych.plugins.parameterType.STRING,
                default: '#666666',
                description: "default color of all circles"
            },
            pixel_per_degree: {
                type:jsPsych.plugins.parameterType.INT,
                default: 3.1415926535 * 10,
                description: 'How many pixels represent on degree visual angle'
            },
            accepted_touch_distance: {
                type:jsPsych.plugins.parameterType.INT,
                default: 1.5,
                description: 'How far away the touch is allowed to be from the dot in dva '
            }
        },
    };

    plugin.trial = function (display_element, trial) {

        // set the condition of the experiment
        let response_on = 'touchstart';
        let response_off = 'touchend';

        // adjust the size of elements
        let target_pos_x = trial.target_pos_x.map(elem => elem * trial.pixel_per_degree)
        let target_pos_y = trial.target_pos_y.map(elem => elem * trial.pixel_per_degree)
        let shifted_target_pos_x = trial.shifted_target_pos_x.map(elem => elem * trial.pixel_per_degree)
        let shifted_target_pos_y = trial.shifted_target_pos_y.map(elem => elem * trial.pixel_per_degree)

        let circle_radius = trial.circle_radius * trial.pixel_per_degree
        let accepted_touch_distance = trial.accepted_touch_distance * trial.pixel_per_degree

        // integrate more than one flash:
        let first_change_onset;
        let next_change_onset;
        let change_onset = Object.assign([], trial.change_onset);

        next_change_onset = change_onset.shift();
        first_change_onset = next_change_onset;

        // copy parameters from trial
        let flash_duration = trial.flash_duration;
        let trial_duration = trial.trial_duration;

        // timing stuff
        let start_time;
        let end_time;
        let flash_on_time;
        let flash_on_times = [];
        let flash_off_time;
        let flash_off_times = [];
        let animation_frame_timestamps = [];

        // create a canvas element
        display_element.innerHTML = '<canvas></canvas>';

        // initialize the canvas
        let canvas = document.querySelector('canvas');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        // get canvas context
        let c = canvas.getContext('2d');

        // initialize an animation request handler
        let AnimationRequest;

        // now, the interaction
        let screen_selected_at = {
            x: undefined,
            y: undefined,
        };

        let touchX = [];
        let touchY = [];
        let choice_order = [];
        let touch_on_time = [];
        let touch_off_time = [];

        let handle_interaction = function(event){
            if (start_time===undefined){
                start_time = event.timeStamp;
            }
            screen_selected_at.x = event.x || event.pageX || event.touches[0].clientX;
            screen_selected_at.y = event.y || event.pageY || event.touches[0].clientY;
            touchX.push(screen_selected_at.x);
            touchY.push(screen_selected_at.y);
            touch_on_time.push(event.timeStamp);
        }

        let handle_release = function(event){
          touch_off_time.push(event.timeStamp);
        };

        let init_circles = function (x_positions, x_positions_shifted, y_positions, y_positions_shifted) {
            let target_circles = [];
            for (let i = 0; i < x_positions.length; i++) {
                let x = x_positions[i] + window.innerWidth / 2;
                let y = y_positions[i] + window.innerHeight / 2;
                let x_shifted = x_positions_shifted[i] + window.innerWidth/2;
                let y_shifted = y_positions_shifted[i] + window.innerHeight/2;
                target_circles.push(new Circle(x, x_shifted, y, y_shifted, circle_radius, trial.circle_color, i, c));
            }
            return target_circles;
        };

        let perform_updates = function (shift, circles, color, rect) {
            for (let i = 0; i < circles.length; i++) {
                let x = [circles[i].x_original, circles[i].x_shift][+shift];
                let y = [circles[i].y_original, circles[i].y_shift][+shift];
                circles[i].change_position(x, y);

                if (screen_selected_at.x - x < accepted_touch_distance && screen_selected_at.x - x > -accepted_touch_distance
                && screen_selected_at.y - y < accepted_touch_distance && screen_selected_at.y -y > -accepted_touch_distance){
                    choice_order.push(circles[i].position)
                    // remove circle
                    circles.splice(i,1);
                    screen_selected_at.x = undefined;
                    screen_selected_at.y = undefined;
                }
            }
            rect.change_color(color);
        };

        let get_current_position_and_color = function (timestamp){
            let after_first_change = timestamp > first_change_onset;
            let after_next_change = timestamp > next_change_onset;
            let before_flash_off = flash_on_time===undefined || timestamp < (flash_on_time + flash_duration);
            let color = [trial.background_color, trial.flash_color][+(after_next_change && before_flash_off)];

            if (after_next_change && flash_on_time===undefined){
                flash_on_time = timestamp;
                flash_on_times.push(timestamp);
            }
            if (before_flash_off===false && flash_off_time===undefined){
                flash_off_times.push(timestamp);
                next_change_onset = change_onset.shift();
                flash_on_time = undefined;
            }
            return [after_first_change, color];
        };

        let animate = function (timestamp) {
            AnimationRequest = requestAnimationFrame(animate);
            let repaint_values = get_current_position_and_color(timestamp - start_time);
            perform_updates(repaint_values[0], target_circles, repaint_values[1], rectangle);
            c.clearRect(0, 0, innerWidth, innerHeight);
            rectangle.draw();
            for (let i = 0; i < target_circles.length; i++) {
                target_circles[i].draw();
            }
            animation_frame_timestamps.push(timestamp);

            // check if trial is over
            if (timestamp-start_time >= trial.trial_duration || choice_order.length===nTargets){
                end_time = timestamp;
                end_trial();
            }
        };

        let end_trial = function () {
            // break request animation frame loop
            cancelAnimationFrame(AnimationRequest);

            // kill any remaining setTimeout handlers
            jsPsych.pluginAPI.clearAllTimeouts();

            // remove window wide event listeners
            window.removeEventListener(response_on, handle_interaction)
            window.removeEventListener(response_off, handle_release);

            // check choice order
            let newA = [];
            // compute difference between every choice
            for (let i = 1; i < choice_order.length; i++) newA.push(choice_order[i] - choice_order[i - 1]);

            // gather the data to store for the trial
            let trial_data = {
                //timing
                "startTime": start_time, // trial started (first button pressed) - timestamp
                "endTime": end_time, // trial ended (last button pressed) - timestamp
                "flashOnTime": flash_on_times,// flash appeared - timestamp
                "flashOffTime": flash_off_times, // flash disappeared - timestamp
                "touchOn": touch_on_time, // when buttons were pressed - array of timestamps
                "touchOff": touch_off_time, // when buttons were released - array of timestamps
                "scheduled_change_onset": trial.change_onset, // in case the participant finishes before flashes appeared

                "flash_duration": flash_duration,
                "change_onset": first_change_onset,
                "trial_duration": trial_duration,
                "animation_timestamps": animation_frame_timestamps,

                // coordinates
                "touchX": touchX, // X coordinates of touches - array
                "touchY": touchY, // Y coordinates of touches - array
                "choiceOrder": choice_order, // the order in which all stimuli were pressed
                "position_x": target_pos_x, // the x positions of all dots
                "position_y": target_pos_y, // the y positions of all dots
                "shifted_position_x": shifted_target_pos_x, // the x positions of all dots
                "shifted_position_y": shifted_target_pos_y, // the y positions of all dots

                //booleans
                "lateResponse": choice_order.length!==nTargets, // if all targets were collected
                "orderResponse": newA.every((val) => val === 1), // if the response was in order
                "tooManyTouches": touchX.length > nTargets, // if the screen was touched at too often
                "screenInLandscape": window.innerHeight < window.innerWidth, // if the screen was in a correct orientation
                "success": choice_order.length===nTargets && newA.every((val) => val === 1) &&
                    touchX.length === nTargets && window.innerHeight < window.innerWidth,
                // other
                "windowWidth": window.innerWidth, // the width of the screen
                "windowHeight": window.innerHeight, // the height of the screen
                "userInfo": navigator.userAgent, // some information about the user device
                "platform": navigator.platform, // some information about the web browser
            };
            // clear the display
            display_element.innerHTML = '';
            // reset theme
            switch_custom_theme('jspsych-6.3.1/css/jspsych.css');
            // move on to the next trial after the waiting time
            setTimeout(jsPsych.finishTrial, trial.wait_after, trial_data);
        };

        // draw an array of circles
        let nTargets = target_pos_x.length;
        let target_circles = init_circles(target_pos_x, shifted_target_pos_x, target_pos_y, shifted_target_pos_y)

        // draw the rectangles for the flash
        // Todo: write into one object on canvas
        let rectangle = new Rectangle(0, 0, innerWidth, innerHeight, trial.background_color, c);

        window.addEventListener(response_on, handle_interaction);
        window.addEventListener(response_off, handle_release);

        let pre_flip = 0
        let draw_empty_canvas = function(){
            if (pre_flip < 10){
                requestAnimationFrame(draw_empty_canvas)
            } else {
                setTimeout(requestAnimationFrame, 100, animate)
            }
            c.clearRect(0, 0, innerWidth, innerHeight);
            pre_flip += 1;
        }

        let start_running_after_delay = function(delay){
          switch_custom_theme('custom_styles.css');
          requestAnimationFrame(draw_empty_canvas);
        };
        start_running_after_delay(100);
    };

    return plugin;
})();
