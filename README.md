<img src="http://content.nicokratky.me/flow-logo/logo-horizontal.png" alt="fl0w logo" height="70">
# fl0w

## Documentation

fl0w’s main objective is to reduce compile time to a minimum by offloading it to a separate computer in addition to offering robot remote control capabilities while also moving all robot programming into Sublime Text.

## Getting Started

These instructions give the most direct way to a working fl0w environment.

### System Requirements

||**Support**|
|------|-----------|
|**OS X**|![](https://img.shields.io/badge/status-supported-brightgreen.svg)|
|**Linux**|![](https://img.shields.io/badge/status-supported-brightgreen.svg)|
|**Windows**|![](https://img.shields.io/badge/status-kinda%20supported-yellow.svg)|

A Unix like operating system running on an ARMv7 bases device with clang or gcc and Python 3.5 is required on the server.
The Sublime Text client is platform independent, although only OS X and Linux are officially supported.

### Getting Sources

**Via HTTPS**

    git clone https://github.com/robot0nfire.com/fl0w.git
    cd fl0w

**Via SSH**

    git clone git@github.com:robot0nfire/fl0w.git
    cd fl0w

For setting up the environment just run:

    ./setup.py

## Using fl0w

1. Connect to a fl0w server in Sublime Text (Tools → Command Pallet → fl0w: Menu → Connect)

2. Connect a Wallaby

3. Create `hello_world.c` in Sublime Text

4. Content of hello_world.c: 
    ```c
    #include <stdio.h>  
    main() { 
        printf(“Hello World”);
    } 
    ```

5. Save

6. Open Wallaby Control   (Tools → Command Pallet → fl0w: Menu → Wallaby Control)
    - Choose Wallaby from list
    - Use Run
    - Select hello_world

7. Program will now run on the selected Wallaby and output will be piped into the Sublime Text console (View → Show Console)

## Credits

fl0w was creating using following libraries:

- watchdog ([https://github.com/gorakhargosh/watchdog](https://github.com/gorakhargosh/watchdog))

## Licensing

See [LICENSE](LICENSE)

[![forthebadge](http://forthebadge.com/images/badges/built-by-hipsters.svg)](http://forthebadge.com)
