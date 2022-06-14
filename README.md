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
5. Create a sample configuration file:
   ```shell
   python3 -m p2p_nse5 -c <PATH_TO_CONFIG_FILE> config
   ```
6. Edit the newly created configuration file to fit your setup.
7. Run the NSE module:
   ```shell
   python3 -m p2p_nse5 -c <PATH_TO_CONFIG_FILE> run
   ```
