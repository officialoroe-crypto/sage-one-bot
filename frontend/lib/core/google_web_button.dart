import 'package:flutter/material.dart';

import 'google_web_button_stub.dart'
    if (dart.library.js_interop) 'google_web_button_web.dart' as implementation;

Widget buildGoogleWebButton() => implementation.buildGoogleWebButton();
