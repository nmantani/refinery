# Binary Refinery
[![Documentation](.docbadge.svg)][docs]
[![Test Status](https://github.com/binref/refinery/actions/workflows/test.yml/badge.svg)][tests]
[![Code Coverage](https://codecov.io/gh/binref/refinery/branch/master/graph/badge.svg)][codecov]
[![PyPI Version](https://badge.fury.io/py/binary-refinery.svg)][pypi]
```
  __     __  High Octane Triage Analysis          __
  ||    _||______ __       __________     _____   ||
  ||    \||___   \__| ____/   ______/___ / ____\  ||
==||=====||  | __/  |/    \  /==|  / __ \   __\===]|
  '======||  |   \  |   |  \_  _| \  ___/|  |     ||
         ||____  /__|___|__/  / |  \____]|  |     ||
=========''====\/=========/  /==|__|=====|__|======'
                         \  /
                          \/
```
The Binary Refinery&trade; is a collection of Python scripts that implement transformations of binary data such as compression and encryption.
We will often refer to it simply by _refinery_, which is also the name of the corresponding package.
The scripts are designed to exclusively read input from stdin and write output to stdout.
This way, the individual units can be chained with the piping operator `|` on the commandline to perform more complex tasks.
The project was born to aid with malware triage, and is an attempt to implement something like [CyberChef](https://github.com/gchq/CyberChef) on the commandline.

The main philosophy of the refinery is that every script should be a unit in the sense that it does _one_ job.
It is always a case by case decision, but it is generally desirable to reduce the number of possible arguments of each script to a minimum and prefer strong capsulation if some functionality could be provided by a separate unit. 

## Documentation

The main documentation is [generated automatically from the source code][docs];
it serves primarily as a reference but also contains the specification for the three fundamental concepts of the toolkit:
[framing][frame], [multibin arguments][argformats], and [meta variables][meta]. 

In recognition of the fact that reference documentation can be somewhat dry,
there is an ongoing effort to produce a series of [tutorials](tutorials) and there are a few additional resources:

- [OALabs](https://www.youtube.com/c/OALabs) was kind enough to let me [demo the toolkit in a feature video](https://www.youtube.com/watch?v=4gTaGfFyMK4).
- [Johannes Bader](https://bin.re/) wrote an amazing [blog post about how to analyze TA551 malspam with binary refinery](https://bin.re/blog/analysing-ta551-malspam-with-binary-refinery/). It should really be turned into a tutorial at some point.

Full-text search of the description and help text for every unit is also available on the command line, via the provided `binref` command.

## License

The Binary Refinery is (c) 2019 Jesko Hüttenhain, and published under a [3-Clause BSD License][license].
This repository also contains [a copy of the full license text](LICENSE). 
If you want to do something with it that's not covered by this license, please feel free to contact the author.

## Warnings & Advice

The refinery requires at least **Python 3.7**.
It is recommended to install it into its own [virtual environment][venv]:
The package has a **lot** of dependencies, and installing it into your global Python is somewhat prone to dependency conflicts.
Also, since the toolkit introduces a large number of new commands,
there is a good chance that some of these will clash on some systems,
and keeping them in their own separate virtual environment is one way to prevent that.

If you want to have all refinery commands available in your shell at all times (i.e. without having to switch to a custom virtual environment),
you also have the option to choose a _prefix_ for the installation,
which will be put in front of every command shim that is installed.
For example, if you choose `r.` as your prefix, then the [emit][] unit will be installed as the command `r.emit`.
An added benefit is that you can type `r.` and hammer <kbd>Tab</kbd> twice to get a list of all available refinery commands.
Note however that no prefix is assumed in documentation and it is a development goal of refinery to _not_ clash on most systems.
The author does not use a prefix and provides this option as a safety blanket. 

## Installation

The most straightforward way to install and update refinery is via pip:
```
pip install -U binary-refinery
```
If you want to choose a prefix for the installed commands, you have to specify it via the environment variable `REFINERY_PREFIX`.
For example, the following command will install refinery into the current Python environment with prefix `r.` on Linux:
```bash
REFINERY_PREFIX=r. pip install -U binary-refinery
```
On Windows, you would have to run the following commands:
```batch
set REFINERY_PREFIX=r.
pip install -U binary-refinery
```
Specifying the special prefix `!` will have the effect that no shell commands are created at all,
and binary refinery will be installed only as a library.
If you want to install the current refinery `HEAD`, you can repeat all of the above steps, specifying this repository instead of the pip package.
For example, the following will install the very latest refinery commit:
```
pip install -U git+git://github.com/binref/refinery.git
```

## Shell Support

The following is a summary of how well various shell environments are currently supported:

| Shell      | Platform | State           | Comment                                                          |
|:-----------|:---------|:----------------|:-----------------------------------------------------------------|
| Bash       | Posix    | 🔵 Good         | Used occasionally by the author.                                 |
| CMD        | Windows  | 🔵 Good         | Used extensively by the author.                                  |
| PowerShell | Windows  | 🟡 Reasonable   | It [just works if the PowerShell version is at least 7.4.][psh1] |
| Zsh        | Posix    | 🟠 Minor Issues | Following a [discussion][zsh1], there is a [fix][zsh2].          |

If you are using a different shell and have some feedback to share, please [let me know](https://github.com/binref/refinery/discussions)!

## Heavyweight Dependencies

There are some units that have rather heavy-weight dependencies.
For example, [pcap][] is the only unit that requires a packet capture file parsing library.
These libraries are not installed by default to keep the installation time for refinery at a reasonable level for first-time users.
The corresponding units will tell you what to do when their dependency is missing:
```
$ emit data.pcap | pcap [| peek ]
(13:37:00) failure in pcap: dependency pypcapkit[scapy] is missing; run pip install 'pypcapkit[scapy]'
```
You can then install these missing dependencies manually.
If you do not want to be bothered by missing dependencies and don't mind a long refinery installation, you can install the package as follows:
```
pip install -U binary-refinery[all]
```
which will install _all_ dependencies on top of the required ones.
More precisely, there are the following extra categories available:

| Name       | Included Dependencies                                             |
|------------|-------------------------------------------------------------------|
| `all`      | all dependencies for all refinery units                           |
| `arc`      | all archiving-related dependencies (i.e. 7zip support)            |
| `default`  | recommended selection of reasonable dependencies, author's choice |
| `display`  | the packages `colorama` and `jsbeautifier`                        |
| `extended` | an extended selection, excluding only the most heavyweight ones   |
| `formats`  | all dependencies related to parsing of various file formats       |
| `office`   | subset of `formats`; all office-related parsing dependencies      |
| `python`   | packages related to Python decompilation                          |

You can specify any combination of these to the installation to have some control over trading dependencies for capabilities.

## Bleeding Edge

Alternatively, you can clone this repository and use the scripts [update.sh](update.sh) (on Linux) or [update.ps1](update.ps1) (on Windows) to install the refinery package into a local virtual environment.
The installation and update process for this method is to simply run the script:
- it pulls the repository,
- activates the virtual environment,
- uninstalls `binary-refinery`,
- and then installs `binary-refinery[all]`.

## Generating Documentation

You can also generate all documentation locally.
To do so, execute the [run-pdoc3.py](run-pdoc3.py) script.
This will **fail** unless you run it from an environment where binary refinery has been installed as a Python package.
To run it, you have to specify the path of a virtual environment as the first command line argument to [run-pdoc3.py](run-pdoc3.py),
which will cause the script to run itself again using the interpreter of that environment.
If you are certain that you want to run [run-pdoc3.py](run-pdoc3.py),
there is a command line switch to force the script to run with the current default Python interpreter.
The script installs the [pdoc3 package][pdoc3] and uses it to generate an HTML documentation for the `refinery` package.
The documentation can then be found in the subdirectory `html` directly next to this readme file.

The [tutorials](tutorials) are Jupyter notebooks which you can simply run and execute if your virtual environment has [Jupyter installed][jupyter].
It's worth pointing out that [Visual Studio Code has very comfortable support for Jupyter][jupyter-vscode].

## Examples

### Basic Examples

The units [emit][] and [dump][] play a special role:
The former is for outputting data while the latter is for dumping data to the clipboard or to disk.
As an example, consider the following pipeline:
```
emit M7EwMzVzBkI3IwNTczM3cyMg2wQA | b64 | zl | hex 
```
Here, we emit the string `M7EwMzVzBkI3IwNTczM3cyMg2wQA`,
base64-decode it using [b64][],
zlib-decompress the result using [zl][],
and finally [hex][]-decode the decompressed data.
Each unit performs the _"decoding"_ operation of a certain transformation by default, but some of them also implement the reverse operation.
If they do, this is always done by providing the command line switch `-R`, or `--reverse`.
You can produce the above base64 string using the following command because [hex][], [zl][], and [b64][] all provide the reverse operation:
```
emit "Hello World" | hex -R | zl -R | b64 -R
```
Given a file `packed.bin` containing a base64 encoded payload buffer, the following pipeline extracts said payload to `payload.bin`:
```
emit packed.bin | carve -l -t1 b64 | b64 | dump payload.bin
```
The [carve][] unit can be used to carve blocks of data out of the input buffer,
in this case it looks for base64 encoded data, sorts them by length (`-l`) and returns the first of these (`-t1`),
which carves the largest base64-looking chunk of data from `packed.bin`.
The data is then base64-decoded and dumped to the file `payload.bin`. 

The unit [pack][], will pick all numeric expressions from a text buffer and turn them into their binary representation.
A simple example is the pipeline
```
emit "0xBA 0xAD 0xC0 0xFF 0xEE" | pack | hex -R 
```
which will output the string `BAADC0FFEE`.

### Short & Sweet

Extract the largest piece of base64 encoded data from a BLOB and decode it:
```
emit file.exe | carve -ds b64
```
Carve a ZIP file from a buffer, pick a DLL from it, and display information about it:
```
emit file.bin | carve-zip | xtzip file.dll | pemeta
```
List PE file sections with their corresponding SHA-256 hash:
```
emit file.exe | vsect [| sha256 -t | cfmt {} {path} ]]
```
Recursively list all files in the current directory with their respective SHA-256 hash:
```
ef "**" [| sha256 -t | cfmt {} {path} ]]
```
Extract indicators from all files recursively enumerated inside the current directory:
```
ef "**" [| xtp -n6 ipv4 socket url email | dedup ]]
```
Convert the hard-coded IP address `0xC0A80C2A` in network byte order to a readable format:
```
emit 0xC0A80C2A | pack -EB4 | pack -R [| sep . ]
```
Perform a single byte XOR brute force and attempt to extract a PE file payload in every iteration:
```
emit file.bin | rep 0x100 [|cm| xor var:index | carve-pe -R | peek | dump {name} ]
```

### Malware Config Examples

Extract a RemCos C2 server:
```
emit c0019718c4d4538452affb97c70d16b7af3e4816d059010c277c4e579075c944 \
  | perc SETTINGS [| put keylen cut::1 | rc4 cut::keylen | xtp socket ]
```
Extract an AgentTesla configuration:
```
emit fb47a566911905d37bdb464a08ca66b9078f18f10411ce019e9d5ab747571b40 \
  | dnfields [| aes x::32 --iv x::16 -Q ]] \
  | rex -M "((??email))\n(.*)\n(.*)\n:Zone" addr={1} pass={2} host={3}
```
Extract the PowerShell payload from a malicious XLS macro dropper:
```
emit 81a1fca7a1fb97fe021a1f2cf0bf9011dd2e72a5864aad674f8fea4ef009417b [ \
  | xlxtr 9.5:11.5 15.15 12.5:14.5 [ \
  | scope -n 3 | chop -t 5 [| sorted -a | snip 2: | sep ] \
  | pack 10 | alu --dec -sN B-S ]] \
  | dump payload.ps1
```
And get the domains for the next stage:
```
emit payload.ps1 
  | carve -sd b64 | zl | deob-ps1 
  | carve -sd b64 | zl | deob-ps1
  | xtp -f domain
```
Extract the configuration of unpacked HawkEye samples:
```
emit ee790d6f09c2292d457cbe92729937e06b3e21eb6b212bf2e32386ba7c2ff22c \
  | put cfg perc[RCDATA]:c:: [\
  | xtp guid | pbkdf2 48 rep[8]:h:00 | cca eat:cfg | aes -Q x::32 --iv x::16 ] \
  | dnds
```
Warzone RAT:
```
emit 4537fab9de768a668ab4e72ae2cce3169b7af2dd36a1723ddab09c04d31d61a5 \
  | vsect .bss | struct I{key:{}}{} [\
  | rc4 eat:key | struct I{host:{}}{port:H} {host:u16}:{port} ]
```
Extract payload from a shellcode loader and carve its c2:
```
emit 58ba30052d249805caae0107a0e2a5a3cb85f3000ba5479fafb7767e2a5a78f3 \
  | rex yara:50607080.* [| struct LL{s:L}{} | xor -B2 accu[s]:@msvc | xtp url ]
```
Extract the malicious downloader payload from a malicious document's text body:
```
emit ee103f8d64cd8fa884ff6a041db2f7aa403c502f54e26337c606044c2f205394 \
  | doctxt | repl drp:c: | carve -s b64 | rev | b64 | rev | ppjscript
```

### AES Encryption

Assume that `data` is a file which was encrypted with 256-bit AES in CBC mode.
The key was derived from the secret passphrase `swordfish` using the PBKDF2 key derivation routine using the salt `s4lty`.
The IV is prefixed to the buffer as the first 16 bytes.
It can be decrypted with the following pipeline:
```
emit data | aes --mode cbc --iv cut::16 pbkdf2[32,s4lty]:swordfish
```
Here, both `cut:0:16` and `pbkdf2[32,s4lty]:swordfish` are multibin arguments that use a special handler.
In this case, `cut:0:16` extracts the slice `0:16` (i.e. the first 16 bytes) from the input data - after application of this multibin handler,
the input data has the first 16 bytes removed and the argument `iv` is set to these exact 16 bytes.
The final argument specifies the 32 byte encryption key:
The handler `pbkdf2[32,s4lty]` on the other hand instructs refinery to create an instance of the pbkdf2 unit as if it had been given the command line parameters `32` and `s4lty` in this order and process the byte string `swordfish` with this unit.
As a simple test, the following pipeline will encrypt and decrypt a sample piece of text:
```
emit "Once upon a time, at the foot of a great mountain ..." ^
    | aes pbkdf2[32,s4lty]:swordfish --iv md5:X -R | ccp md5:X ^
    | aes pbkdf2[32,s4lty]:swordfish --iv cut:0:16 
```


[pdoc3]: https://pdoc3.github.io/pdoc/
[docs]: https://binref.github.io/
[argformats]: https://binref.github.io/lib/argformats.html
[frame]: https://binref.github.io/lib/frame.html
[meta]: https://binref.github.io/lib/meta.html
[license]: https://opensource.org/licenses/BSD-3-Clause
[tests]: https://github.com/binref/refinery/actions
[codecov]: https://codecov.io/gh/binref/refinery/?branch=master
[pypi]: https://pypi.org/project/binary-refinery/
[venv]: https://docs.python.org/3/library/venv.html

[zsh1]: https://github.com/binref/refinery/discussions/18
[zsh2]: shells/zsh
[psh1]: https://github.com/binref/refinery/issues/5

[dump]: https://binref.github.io/#refinery.dump
[emit]: https://binref.github.io/#refinery.emit
[stego]: https://binref.github.io/#refinery.stego
[pcap]: https://binref.github.io/#refinery.pcap
[hex]: https://binref.github.io/#refinery.hex
[zl]: https://binref.github.io/#refinery.zl
[b64]: https://binref.github.io/#refinery.b64
[carve]: https://binref.github.io/#refinery.carve
[pack]: https://binref.github.io/#refinery.pack

[jupyter]: https://jupyter.org/install
[jupyter-vscode]: https://code.visualstudio.com/docs/datascience/jupyter-notebooks
