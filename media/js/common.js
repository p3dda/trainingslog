/*
 Some generic js vars and methods
 */

var dayNamesMin = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];
var monthNames = ['Januar', 'Februar', 'M&auml;rz', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
var monthNamesMin = ['Jan', 'Feb', 'März', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];

/**
 * Checks if a given string is integer or not
 *
 * @param {String|number} val The string in question.
 */
function isInt(val) //noinspection JSLint
{
	var retval;
	if(!val || ( typeof val != "string" || val.constructor != String)) {
		retval = false;
	} else {
		retval = (parseFloat(val) == parseInt(val, 10)) && !isNaN(val);
	}
	return retval;
}


/**
 * Checks if a given string is float or not
 *
 * @param {String|number} val The string in question.
 */
function isFloat(val) {
	var retval;
	if(!val || ( typeof val != "string" || val.constructor != String)) {
		retval = false;
	} else {
		var isNumber = !isNaN(Number(val));
		if(isNumber) {
			retval = val.indexOf('.') != -1;
		} else {
			retval = false;
		}

	}
	return retval;
}

/**
 * Checks if a given string is numeric (int or float)
 * 
 * @param {String} val The string in question.
 */
function isNum(val) {
	return isFloat(val) || isInt(val);
}


/** 
 * Checks if given string is valid time / duration string (hh:mm or hh:mm:ss)
 * 
 * @param {String} val The string in question
 */
function isTime(val) {
	var retval;
	var re = /^(\d\d?):(\d\d)(?::(\d\d))?$/;
	if(!val || ( typeof val != "string" || val.constructor != String)){
		retval = false;
	} else {
		retval = re.test(val)
	}
	return retval
}

/** 
 * Convert given time / duration string to seconds
 * 
 * @param {String} val The time string
 */
function timeToSeconds(val) {
	var re = /^(\d\d?):(\d\d)(?::(\d\d))?$/g;
	var seconds = 0;
	var match = re.exec(val);
	if (match) {
		if(match.length < 3){
			return (false);
		}
		seconds = seconds + parseInt(match[1])*3600;
		seconds = seconds + parseInt(match[2])*60;
		
		if(match[3] !== undefined) {
			seconds = seconds + parseInt(match[3]);
		}
	}
	return seconds
}

/** 
 * Convert speed float to pace (km/h -> min/km)
 * 
 * @param {float} val The given speed
 */
function speedToPace(val){
	var timeString;
	if(val!=null) {
		var secondsPerKm = 3600/val;
		
		var minutes = Math.floor(secondsPerKm / 60);
		var seconds = Math.floor(secondsPerKm % 60);
		
		timeString = minutes + ':' + pad(seconds, 2);
	} else {
		timeString = "";
	}
	return timeString;
}

/** 
 * Convert pace to speed (min/km --> km/h)
 * 
 * @param {string} val The given speed
 */
function paceToSpeed(val){
	var speed;
	if(val!=null) {
		var pace = val.split(':');
		
		var seconds = parseInt(pace[0], 10) * 60 + parseInt(pace[1], 10);
		speed =  3600.0 / seconds;
	} else {
		speed = 0.0;
	}
	return speed;
}

/**
 * Convert given duration int (seconds) to time (d hh:mm:ss) or (hh:mm:ss) or (mm:ss)
 *
 * @param val The time in seconds
 * @param withHours with hours prefix
 * @param withDays with days prefix
 */
function secondsToTime(val, withHours, withDays){
	if(withHours==null){
		withHours = true;
	}
	if(withDays==null){
		withDays = false;
	}

	if(withDays) {
		var days = Math.floor(val/86400);
		val %= 86400;
	}
	if(withHours) {
		var hours =  Math.floor(val/3600);
		val %= 3600;
//		var minutes = ( Math.floor(val/60)) % 60;
	}
	var minutes = ( Math.floor(val/60)) % 60;
	var seconds = Math.floor(val % 60);
//	var timeString = '%02d:%02d:%02d'.sprintf(hours, minutes, seconds);

	var timeString="";

	if(withDays){
		if(days==1){
			timeString = days + ' Tag '
		} else {
			timeString = days + ' Tage '
		}
	}
	if(withHours) {
		timeString += pad(hours, 2) + ':' + pad(minutes, 2) + ':' + pad(seconds, 2);
	} else {
		timeString += pad(minutes, 2) + ':' + pad(seconds, 2);
	}

	return timeString;
}


/**
 * Return an integer as string with leading zeroes
 * 
 * @param {number} number Number to convert
 * @param {number} length Length of resulting string
 */
function pad(number, length) {
	var str = '' + number;
	while (str.length < length) {
		str = '0' + str;
	}
	return str;
}

/**
 * Extend Date object with function getWeek returning week of year
 */
Date.prototype.getWeek = function() {
	var onejan = new Date(this.getFullYear(),0,1);
	return Math.ceil((((this - onejan) / 86400000) + onejan.getDay()+1)/7);
};


/**
 * Transpose 2-dimensional array
 */
function transpose(a)
{
  return Object.keys(a[0]).map(function (c) { return a.map(function (r) { return r[c]; }); });
}

/**
 * Encode string to base64
 * @param inp String to encode
 */
function encode64(inp){
    var key="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=";
    var chrA,chrB,chrC,encA,encB,i=0,out="";
    while(i<inp.length){
        chrA=inp.charCodeAt(i++);if(chrA>127) chrA=88;
        chrB=inp.charCodeAt(i++);if(chrB>127) chrB=88;
        chrC=inp.charCodeAt(i++);if(chrC>127) chrC=88;
        if(isNaN(chrC)) {encB=64;chrC=0;} else encB=chrC&63;
        if(isNaN(chrB)) {encA=64;chrB=0;} else encA=((chrB<<2)|(chrC>>6))&63;
        out+=key.charAt((chrA>>2)&63)+key.charAt(((chrA<<4)|(chrB>>4))&63)+key.charAt(encA)+key.charAt(encB);
    }
    return encodeURIComponent(out);
}

/* Base64 conversion methods.
 * Copyright (c) 2006 by Ali Farhadi.
 * released under the terms of the Gnu Public License.
 * see the GPL for details.
 *
 * Email: ali[at]farhadi[dot]ir
 * Website: http://farhadi.ir/
 */

//Encodes data to Base64 format
function base64Encode(data){
	if (typeof(btoa) === 'function') return btoa(data);//use internal base64 functions if available (gecko only)
	var b64_map = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
	var byteA, byteB, byteC;
	var chrA, chrB, chrC, chrD;
	var result = []; //array is used instead of string because in most of browsers working with large arrays is faster than working with large strings
	var j=0;
	for (var i=0; i<data.length; i+=3) {
		byteA = data.charCodeAt(i);
		byteB = data.charCodeAt(i+1);
		byteC = data.charCodeAt(i+2);
		chrA = byteA >> 2;
		chrB = ((byteA & 3) << 4) | (byteB >> 4);
		chrC = ((byteB & 15) << 2) | (byteC >> 6);
		chrD = byteC & 63;

		if (isNaN(byteB)) {
			chrC = chrD = 64;
		} else if (isNaN(byteC)) {
			chrD = 64;
		}

		result[j++] = b64_map.charAt(chrA)+b64_map.charAt(chrB)+b64_map.charAt(chrC)+b64_map.charAt(chrD);
	}

	return result.join('');
}

//Decodes Base64 formated data
function base64Decode(data){
	data = data.replace(/[^a-z0-9\+\/=]/ig, '');// strip none base64 characters
	if (typeof(atob) == 'function') return atob(data);//use internal base64 functions if available (gecko only)
	var b64_map = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
	var byteA, byteB, byteC;
	var chrA, chrB, chrC, chrD;
	var result = []; //array is used instead of string because in most of browsers working with large arrays is faster than working with large strings
	var j=0;
	while ((data.length%4) != 0) {
		data += '=';
	}

	for (var i=0; i<data.length; i+=4) {
		chrA = b64_map.indexOf(data.charAt(i));
		chrB = b64_map.indexOf(data.charAt(i+1));
		chrC = b64_map.indexOf(data.charAt(i+2));
		chrD = b64_map.indexOf(data.charAt(i+3));

		byteA = (chrA << 2) | (chrB >> 4);
		byteB = ((chrB & 15) << 4) | (chrC >> 2);
		byteC = ((chrC & 3) << 6) | chrD;

		result[j++] = String.fromCharCode(byteA);
		if (chrC != 64) result[j++] = String.fromCharCode(byteB);
		if (chrD != 64) result[j++] = String.fromCharCode(byteC);
	}

	return result.join('');
}

function quantile(data, q) {
	var count = data.length;
	//data.sort();
	data.sort(function(a,b){return a - b});
	return data[Math.floor(count*q)];
}