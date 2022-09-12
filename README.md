# P2P Summer Semester 2022: Network Size Estimation (5)

## Setup and execution

1. Make sure you have Python >= 3.9 and a recent enough version of `pip`
   and `venv` / `virtualenv` installed on your system. We currently
   officially support Debian GNU+Linux and Alpine Linux.
2. Clone this repository to your preferred target location.
3. Create and enable your virtual environment in the target location.
   Using `python-venv`, this can be done as follows:
   ```shell
   python3 -m venv venv
   source venv/bin/activate
   ```
4. Install the required packages:
   ```shell
   pip3 install -r requirements.txt
   ```
   On Alpine Linux, you need the extra packages `gcc`, `g++` and `libc-dev`.
5. Create a sample configuration file:
   ```shell
   python3 -m p2p_nse5 new -c <PATH_TO_CONFIG_FILE>
   ```
6. Edit the newly created configuration file to fit your setup.
   In case the required RSA private key has not yet been generated,
   this can be accomplished using the subcommand `generate`:
   ```shell
   python3 -m p2p_nse5 generate <PATH_TO_NEW_RSA_FILE>
   ```
7. Run the NSE module:
   ```shell
   python3 -m p2p_nse5 run -c <PATH_TO_CONFIG_FILE>
   ```

The `run` command supports a set of runtime options to make it easy to
run multiple instances with the same configuration file in parallel:

```
usage: p2p_nse5 run [-h] [-c <file>] [-d <URL>] [-g <address>] [-l <address>] [-p <file>]

optional arguments:
  -h, --help    show this help message and exit
  -c <file>     configuration filename (defaults to 'config.ini')
  -d <URL>      overwrite full database connection string
  -g <address>  overwrite address of the Gossip API server
  -l <address>  overwrite local API listen address
  -p <file>     overwrite path to the RSA private key
```

## Documentation

Project reports can be found in the directory `docs`.

Source code documentation can be found in the directory `sphinx`. In order to
generate the HTML version of the source code documentation, use the following:

```shell
cd sphinx
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r ../requirements.txt
make html
```

## License

This project is licensed under [AGPLv3](./LICENSE).
