/*
 Some generic js vars and methods
 */

var dayNamesMin = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];
var monthNames = ['Januar', 'Februar', 'M&auml;rz', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
var monthNamesMin = ['Jan', 'Feb', 'M�rz', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];

/**
 * Checks if a given string is integer or not
 *
 * @param {String} val The string in question.
 */
function isInt(val) {
	if(!val || ( typeof val != "string" || val.constructor != String)) {
		return (false);
	}
	if((parseFloat(val) == parseInt(val, 10)) && !isNaN(val)) {
		return true;
	} else {
		return false;
	}
}


/**
 * Checks if a given string is float or not
 *
 * @param {String} val The string in question.
 */
function isFloat(val) {
	if(!val || ( typeof val != "string" || val.constructor != String)) {
		return (false);
	}
	var isNumber = !isNaN(new Number(val));
	if(isNumber) {
		if(val.indexOf('.') != -1) {
			return (true);
		} else {
			return (false);
		}
	} else {
		return (false);
	}
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
	var re = /^(\d\d?):(\d\d)(?::(\d\d))?$/;
	if(!val || ( typeof val != "string" || val.constructor != String)){
		return (false);
	}
	return (re.test(val));
}

/** 
 * Convert given time / duration string to seconds
 * 
 * @param {String} val The time string
 */
function timeToSeconds(val) {
	var re = /^(\d\d?):(\d\d)(?::(\d\d))?$/g;
	var seconds = 0
	match = re.exec(val);
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
	if(val!=null) {
		secondsPerKm = 3600/val;
		
		minutes = Math.floor(secondsPerKm / 60);
		seconds = Math.floor(secondsPerKm % 60);
		
		var timeString = minutes + ':' + pad(seconds, 2);
	} else {
		var timeString = "";
	}
	return timeString;
}

/** 
 * Convert pace to speed (min/km --> km/h)
 * 
 * @param {string} val The given speed
 */
function paceToSpeed(val){
	if(val!=null) {
		pace = val.split(':');
		
		seconds = parseInt(pace[0], 10) * 60 + parseInt(pace[1], 10);
		var speed =  3600.0 / seconds;
	} else {
		var speed = 0.0;
	}
	return speed;
}

/**
 * Convert given duration int (seconds) to time (hh:mm:ss)
 * 
 * @param {Integer} val The time in seconds
 */
function secondsToTime(val, with_hours, with_days){
	if(with_hours==null){
		with_hours = true;
	}
	if(with_days==null){
		with_days = false;
	}

	if(with_days) {
		var days = Math.floor(val/86400);
		val %= 86400;
	}
	if(with_hours) {
		var hours =  Math.floor(val/3600);
		val %= 3600
//		var minutes = ( Math.floor(val/60)) % 60;
	}
	var minutes = ( Math.floor(val/60)) % 60;
	var seconds = Math.floor(val % 60);
//	var timeString = '%02d:%02d:%02d'.sprintf(hours, minutes, seconds);

	var timeString="";

	if(with_days){
		if(days==1){
			timeString = days + ' Tag '
		} else {
			timeString = days + ' Tage '
		}
	}
	if(with_hours) {
		timeString += pad(hours, 2) + ':' + pad(minutes, 2) + ':' + pad(seconds, 2);
	} else {
		timeString += pad(minutes, 2) + ':' + pad(seconds, 2);
	}

	return timeString;
}


/**
 * Return an integer as string with leading zeroes
 * 
 * @param {Integer} number Number to convert
 * @param {Integer} length Length of resulting string
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
}


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
    var chr1,chr2,chr3,enc3,enc4,i=0,out="";
    while(i<inp.length){
        chr1=inp.charCodeAt(i++);if(chr1>127) chr1=88;
        chr2=inp.charCodeAt(i++);if(chr2>127) chr2=88;
        chr3=inp.charCodeAt(i++);if(chr3>127) chr3=88;
        if(isNaN(chr3)) {enc4=64;chr3=0;} else enc4=chr3&63
        if(isNaN(chr2)) {enc3=64;chr2=0;} else enc3=((chr2<<2)|(chr3>>6))&63
        out+=key.charAt((chr1>>2)&63)+key.charAt(((chr1<<4)|(chr2>>4))&63)+key.charAt(enc3)+key.charAt(enc4);
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
	if (typeof(btoa) == 'function') return btoa(data);//use internal base64 functions if available (gecko only)
	var b64_map = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
	var byte1, byte2, byte3;
	var ch1, ch2, ch3, ch4;
	var result = new Array(); //array is used instead of string because in most of browsers working with large arrays is faster than working with large strings
	var j=0;
	for (var i=0; i<data.length; i+=3) {
		byte1 = data.charCodeAt(i);
		byte2 = data.charCodeAt(i+1);
		byte3 = data.charCodeAt(i+2);
		ch1 = byte1 >> 2;
		ch2 = ((byte1 & 3) << 4) | (byte2 >> 4);
		ch3 = ((byte2 & 15) << 2) | (byte3 >> 6);
		ch4 = byte3 & 63;

		if (isNaN(byte2)) {
			ch3 = ch4 = 64;
		} else if (isNaN(byte3)) {
			ch4 = 64;
		}

		result[j++] = b64_map.charAt(ch1)+b64_map.charAt(ch2)+b64_map.charAt(ch3)+b64_map.charAt(ch4);
	}

	return result.join('');
}

//Decodes Base64 formated data
function base64Decode(data){
	data = data.replace(/[^a-z0-9\+\/=]/ig, '');// strip none base64 characters
	if (typeof(atob) == 'function') return atob(data);//use internal base64 functions if available (gecko only)
	var b64_map = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
	var byte1, byte2, byte3;
	var ch1, ch2, ch3, ch4;
	var result = new Array(); //array is used instead of string because in most of browsers working with large arrays is faster than working with large strings
	var j=0;
	while ((data.length%4) != 0) {
		data += '=';
	}

	for (var i=0; i<data.length; i+=4) {
		ch1 = b64_map.indexOf(data.charAt(i));
		ch2 = b64_map.indexOf(data.charAt(i+1));
		ch3 = b64_map.indexOf(data.charAt(i+2));
		ch4 = b64_map.indexOf(data.charAt(i+3));

		byte1 = (ch1 << 2) | (ch2 >> 4);
		byte2 = ((ch2 & 15) << 4) | (ch3 >> 2);
		byte3 = ((ch3 & 3) << 6) | ch4;

		result[j++] = String.fromCharCode(byte1);
		if (ch3 != 64) result[j++] = String.fromCharCode(byte2);
		if (ch4 != 64) result[j++] = String.fromCharCode(byte3);
	}

	return result.join('');
}

function quantile(data, q) {
	var count = data.length;
	//data.sort();
	data.sort(function(a,b){return a - b})
	return data[Math.floor(count*q)];
}