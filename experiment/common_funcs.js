
function check_screen_validity(){
    let touchscreen = window.matchMedia("(pointer: coarse)").matches;
    let width_ok = window.screen.width >= 490;
    let height_ok = window.screen.height >= 300;
    let landscape_ok = window.innerWidth > window.innerHeight;
    let apple = ['iPad Simulator', 'iPhone Simulator', 'iPod Simulator', 'iPad', 'iPhone', 'iPod'].includes(navigator.platform);
    let ua = navigator.userAgent.toLowerCase();
    let safari = false;
    if (ua.indexOf('safari') != -1) {
      if (ua.indexOf('chrome') > -1) {
        safari = false; // Chrome
      } else {
        safari = true; // Safari
      }
    }
    if (jatos.urlQueryParameters.KNOCKKNOCK === 'martin'){
        return true
    } else {
        return touchscreen && width_ok && height_ok && landscape_ok && !apple && !safari
    }
}

function check_calibration_validity(calibration_data){
    // screen width is larger than 17 dva (12 cm phone 40 cm away)
    // 14 dva is the minimum we need to show our stimuli!
    // distance between 20 and 60 cm
    let calibration_valid = calibration_data.win_width_deg >= 17 &&
        calibration_data.view_dist_mm >= 200 &&
        calibration_data.view_dist_mm <= 600
    return calibration_valid
}

function Circle(x, x_shift,y, y_shift, rad, color, pos, c){
  this.x = x;
  this.y = y;
  this.x_original = x;
  this.y_original = y;
  this.x_shift = x_shift;
  this.y_shift = y_shift;
  this.rad = rad;
  this.color = color;
  this.position = pos;

  this.draw = function(){
    c.beginPath();
    c.arc(this.x, this.y, this.rad, 0, Math.PI*2, false);
    c.fillStyle = this.color;
    c.fill();
  }
  this.change_position = function(x,y){
    this.x = x;
    this.y = y;
  }
  this.change_radius = function(rad){
    this.rad = rad;
  }
  this.change_color = function(color){
    this.color = color;
  }
}

function Rectangle(x,y, width, height, color, c){
  this.x = x;
  this.y = y;
  this.width = width;
  this.height = height;
  this.color = color;
  this.original_color = color;

  this.draw = function(){
    c.beginPath();
    c.fillStyle = this.color;
    c.fillRect(this.x, this.y, this.width, this.height);
  }
  this.change_color = function(color){
    this.color = color
  }
}

function make_equal_distance_array(startValue, stopValue, nEntries) {
  let eq_dist_arr = [];
  let step = (stopValue - startValue) / (nEntries - 1);
  for (let i = 0; i < nEntries; i++) {
    eq_dist_arr.push(startValue + (step * i));
  }
  return eq_dist_arr;
}

function Serial_canvas_loop(nTrials, cFlash, cJump, maxFlashTime, twSize, minxPos, maxxPos, minyPos, maxyPos, nDots,
                            randomPosShift, nFlashes) {
    let T; // the trials
    let nT; // number of trials per condition
    let cF; // flash or no flash
    let cJ; // jump or no jump
    let tW; // the time window
    let tP; // the target position
    let nF; // number of flashes
    let ID = 0; // a trial ID
    let targetPosX; // the array with target positions in every trial
    let targetPosY; // the array with target positions in every trial
    let newTargetPosX; // the array with after jump target positions in every trial
    let newTargetPosY; // the array with after jump target positions in every trial
    let flashOnsets; // array with flash onset times
    let test_stimuli = []; // the array that will later hold our design structure

    let PosX = make_equal_distance_array(minxPos, maxxPos, nDots);
    let PosY = make_equal_distance_array(minyPos, maxyPos, nDots);

    // loop through all trials
    for (nT = 0; nT < nTrials; nT++) {
        for (cF = 0; cF < cFlash.length; cF++) {
            for (cJ = 0; cJ < cJump.length; cJ++) {
                // loop through all time windows
                for (tW = 0; tW < maxFlashTime; tW = tW + twSize) {
                    targetPosX = []; // set the target positions to 0
                    newTargetPosX = []; // set the new target position array to empty
                    for (tP = 0; tP < PosX.length; tP++) {
                        targetPosX.push((Math.random() * 2 - 1) * randomPosShift + PosX[tP]);
                        newTargetPosX.push((Math.random() * 2 - 1) * randomPosShift + PosX[tP]);
                    }
                    targetPosY = []; // set the target positions to 0
                    newTargetPosY = []; // set the new target position array to empty
                    for (tP = 0; tP < PosY.length; tP++) {
                        targetPosY.push((Math.random() * 2 - 1) * randomPosShift + PosY[tP]);
                        newTargetPosY.push((Math.random() * 2 - 1) * randomPosShift + PosY[tP]);
                    }
                    flashOnsets = [];
                    for (nF = 0; nF < nFlashes; nF++){
                        flashOnsets.push(tW + Math.random() * twSize)
                    }
                    flashOnsets.sort(function(a, b) {
                        return a - b;
                    });

                    // save the values for the current trial
                    T = {
                        // the time of the flash will be the time window start + a random value between 0
                        // and the size of the time window
                        flashTime: flashOnsets,
                        targetPosX: targetPosX,
                        targetPosY: targetPosY,
                        newTargetPosX: function () {
                            if (cJump[cJ] === 1) {
                                return newTargetPosX
                            } else {
                                return targetPosX
                            }
                        }(),
                        newTargetPosY: function () {
                            if (cJump[cJ] === 1) {
                                return newTargetPosY
                            } else {
                                return targetPosY
                            }
                        }(),
                        flashShown: cFlash[cF],
                        stimJumps: cJump[cJ],
                        flashColor: function () {
                            if (cFlash[cF]) {
                                return '#FFFFFF'
                            } else {
                                return '#666666'
                            }
                        }(),
                        trialID: ID,
                    };
                    // save the trial in our design structure
                    test_stimuli.push(T);
                    // increment the trial ID
                    ID++
                }
            }
        }
    }


    // save the file
    return test_stimuli;
}

function switch_custom_theme(theme_name) {
    let theme = document.getElementById('styles');
    theme.href = theme_name;
}