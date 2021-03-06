def parsefloat(float_string):
	"""It takes a float string ("1,23" or "1,234.567.890") and
	converts it to floating point number (1.23 or 1.234567890).
	@param float_string: String containing float number
	@type float_string: string
	@return float containg converted string value
	@rtype float
	@raise ValueError
	"""
	float_string = str(float_string)
	errormsg = "ValueError: Input must be decimal or integer string"
	try:
		if float_string.count(".") == 1 and float_string.count(",") == 0:
			return float(float_string)
		else:
			midle_string = list(float_string)
			while midle_string.count(".") != 0:
				midle_string.remove(".")
			out_string = str.replace("".join(midle_string), ",", ".")
		return float(out_string)
	except ValueError, error:
		raise
