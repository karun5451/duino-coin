#!/usr/bin/env python3
##########################################
# Duino-Coin Python Miner (v1.9)
# https://github.com/revoxhere/duino-coin
# Distributed under MIT license
# © Duino-Coin Community 2021
##########################################
import socket, statistics, threading, time, re, subprocess, hashlib, configparser, sys, datetime, os # Import libraries
from pathlib import Path
from signal import signal, SIGINT

def install(package):
  subprocess.check_call([sys.executable, "-m", "pip", "install", package])
  os.execl(sys.executable, sys.executable, *sys.argv)

def now():
  return datetime.datetime.now()

try: # Check if cpuinfo is installed
  import cpuinfo
  from multiprocessing import freeze_support
except:
  print(now().strftime("%H:%M:%S ") + "Cpuinfo is not installed. Miner will try to install it. If it fails, please manually install \"py-cpuinfo\" python3 package.\nIf you can't install it, use the Minimal-PC_Miner.")
  install("py-cpuinfo")
  
try: # Check if colorama is installed
  from colorama import init, Fore, Back, Style
except:
  print(now().strftime("%H:%M:%S ") + "Colorama is not installed. Miner will try to install it. If it fails, please manually install \"colorama\" python3 package.\nIf you can't install it, use the Minimal-PC_Miner.")
  install("colorama")

try: # Check if requests is installed
  import requests
except:
  print(now().strftime("%H:%M:%S ") + "Requests is not installed. Miner will try to install it. If it fails, please manually install \"requests\" python3 package.\nIf you can't install it, use the Minimal-PC_Miner.")
  install("requests")

# Global variables
minerVersion = "1.9" # Version number
timeout = 5 # Socket timeout
resourcesFolder = "PCMiner_"+str(minerVersion)+"_resources"
shares = [0, 0]
diff = 0
last_hash_count = 0
khash_count = 0
hash_count = 0
hash_mean = []
donatorrunning = False
debug = False
serveripfile = "https://raw.githubusercontent.com/revoxhere/duino-coin/gh-pages/serverip.txt" # Serverip file
config = configparser.ConfigParser()
autorestart = 0
donationlevel = 0
freeze_support() # If not used, pyinstaller hangs when checking cpuinfo
cpu = cpuinfo.get_cpu_info() # Processor info

if not os.path.exists(resourcesFolder):
    os.mkdir(resourcesFolder) # Create resources folder if it doesn't exist

def debugOutput(text):
  if debug == "True":
    print(now().strftime(Style.DIM + "%H:%M:%S.%f ") + "DEBUG: " + text)

def title(title):
  if os.name == 'nt':
    os.system("title "+title)
  else:
    print('\33]0;'+title+'\a', end='')
    sys.stdout.flush()

def handler(signal_received, frame): # If CTRL+C or SIGINT received, send CLOSE request to server in order to exit gracefully.
  print(now().strftime(Style.DIM + "\n%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.GREEN + Fore.WHITE + " sys "
    + Back.RESET + Fore.YELLOW + " SIGINT detected - Exiting gracefully." + Style.NORMAL + Fore.WHITE + " See you soon!")
  try:
    soc.close()
  except:
    pass
  os._exit(0)
signal(SIGINT, handler) # Enable signal handler

def Greeting(): # Greeting message depending on time
  global autorestart, greeting
  print(Style.RESET_ALL)

  if float(autorestart) <= 0:
    autorestart = 0
    autorestartmessage = "disabled"
  if float(autorestart) > 0:
    autorestartmessage = "every " + str(autorestart) + " minutes"

  current_hour = time.strptime(time.ctime(time.time())).tm_hour

  if current_hour < 12 :
    greeting = "Have a wonderful morning"
  elif current_hour == 12 :
    greeting = "Have a tasty noon"
  elif current_hour > 12 and current_hour < 18 :
    greeting = "Have a peaceful afternoon"
  elif current_hour >= 18 :
    greeting = "Have a cozy evening"
  else:
    greeting = "Welcome back"

  print(" > " + Fore.YELLOW + Style.BRIGHT + "Official Duino-Coin © Python Miner"
  + Style.RESET_ALL + Fore.WHITE + " (v" + str(minerVersion) + ") 2019-2021") # Startup message
  print(" > " + Fore.YELLOW + "https://github.com/revoxhere/duino-coin")
  try:
    print(" > " + Fore.WHITE + "CPU: " + Style.BRIGHT + Fore.YELLOW + str(cpu["brand_raw"]))
  except:
    if debug == "True": raise
  if os.name == 'nt' or os.name == 'posix':
    print(" > " + Fore.WHITE + "Donation level: " +  Style.BRIGHT + Fore.YELLOW + str(donationlevel))
  print(" > " + Fore.WHITE + "Algorithm: " + Style.BRIGHT + Fore.YELLOW + "DUCO-S1")
  print(" > " + Fore.WHITE + "Autorestarter: " + Style.BRIGHT + Fore.YELLOW + str(autorestartmessage))
  print(" > " + Fore.WHITE + str(greeting) + ", " + Style.BRIGHT + Fore.YELLOW + str(username) + "!\n")

  if os.name == 'nt':
    if not Path(resourcesFolder + "/Donate_executable.exe").is_file(): # Initial miner executable section
      debugOutput("OS is Windows, downloading developer donation executable")
      url = 'https://github.com/revoxhere/duino-coin/blob/useful-tools/PoT_auto.exe?raw=true'
      r = requests.get(url)
      with open(resourcesFolder + '/Donate_executable.exe', 'wb') as f:
        f.write(r.content)
  elif os.name == 'posix':
    if not Path(resourcesFolder + "/Donate_executable").is_file(): # Initial miner executable section
      debugOutput("OS is Windows, downloading developer donation executable")
      url = 'https://github.com/revoxhere/duino-coin/blob/useful-tools/DonateExecutableLinux?raw=true'
      r = requests.get(url)
      with open(resourcesFolder + '/Donate_executable', 'wb') as f:
        f.write(r.content)

def hashrateCalculator(): # Hashes/sec calculation
  global last_hash_count, hash_count, khash_count, hash_mean
  last_hash_count = hash_count
  khash_count = last_hash_count / 1000
  hash_mean.append(khash_count) # Calculate average hashrate
  khash_count = round(statistics.mean(hash_mean), 3)
  hash_count = 0 # Reset counter
  threading.Timer(1.0, hashrateCalculator).start() # Run this def every 1s

def autorestarter(): # Autorestarter
  time.sleep(float(autorestart)*60)
  try:
    donateExecutable.terminate() # Stop the donation process (if running)
  except:
    pass
  print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.GREEN + Fore.WHITE + " sys "
    + Back.RESET + Fore.YELLOW + " Autorestarting the miner")
  os.execl(sys.executable, sys.executable, *sys.argv)

def loadConfig(): # Config loading section
  global username, efficiency, autorestart, donationlevel, debug

  if not Path(resourcesFolder + "/Miner_config.cfg").is_file(): # Initial configuration section
    print(Style.BRIGHT + "\nDuino-Coin basic configuration tool\nEdit "+resourcesFolder + "/Miner_config.cfg file later if you want to change it.")
    print(Style.RESET_ALL + "Don't have an Duino-Coin account yet? Use " + Fore.YELLOW + "Wallet" + Fore.WHITE + " to register on server.\n")

    username = input(Style.RESET_ALL + Fore.YELLOW + "Enter your username: " + Style.BRIGHT)
    efficiency = input(Style.RESET_ALL + Fore.YELLOW + "Set mining intensity (1-100)% (recommended: 100): " + Style.BRIGHT)
    autorestart = input(Style.RESET_ALL + Fore.YELLOW + "If you want, set after how many minutes miner will restart (recommended: 30): " + Style.BRIGHT)
    donationlevel = "0"
    if os.name == 'nt' or os.name == 'posix':
      donationlevel = input(Style.RESET_ALL + Fore.YELLOW + "Set developer donation level (0-5) (recommended: 1), this will not reduce your earnings: " + Style.BRIGHT)

    efficiency = re.sub("\D", "", efficiency)  # Check wheter efficiency is correct
    if float(efficiency) > int(100):
      efficiency = 100
    if float(efficiency) < int(1):
      efficiency = 1

    donationlevel = re.sub("\D", "", donationlevel)  # Check wheter donationlevel is correct
    if float(donationlevel) > int(5):
      donationlevel = 5
    if float(donationlevel) < int(0):
      donationlevel = 0

    config['miner'] = { # Format data
    "username": username,
    "efficiency": efficiency,
    "autorestart": autorestart,
    "donate": donationlevel,
    "debug": False}

    with open(resourcesFolder + "/Miner_config.cfg", "w") as configfile: # Write data to file
      config.write(configfile)
    efficiency = (100 - float(efficiency)) * 0.01 # Calulate efficiency for use with sleep function
    print(Style.RESET_ALL + "Config saved! Launching the miner")

  else: # If config already exists, load from it
    config.read(resourcesFolder + "/Miner_config.cfg")
    username = config["miner"]["username"]
    efficiency = config["miner"]["efficiency"]
    efficiency = (100 - float(efficiency)) * 0.01 # Calulate efficiency for use with sleep function
    autorestart = config["miner"]["autorestart"]
    donationlevel = config["miner"]["donate"]
    debug = config["miner"]["debug"]

def Connect(): # Connect to master server section
  global soc, masterServer_address, masterServer_port
  try:
    res = requests.get(serveripfile, data = None) # Use request to grab data from raw github file
    if res.status_code == 200: # Check for response
      content = res.content.decode().splitlines() # Read content and split into lines
      masterServer_address = content[0] # Line 1 = pool address
      masterServer_port = content[1] # Line 2 = pool port
      debugOutput("Retrieved pool IP: " + masterServer_address + ":" + str(masterServer_port))
  except: # If it wasn't, display a message
    print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.BLUE + Fore.WHITE + " net "
      + Back.RESET + Fore.RED + " Error retrieving data from GitHub! Retrying in 10s.")
    if debug == "True": raise
    time.sleep(10)
    Connect()
  try: # Try to connect
    try: # Shutdown previous connections (if any)
      soc.shutdown(socket.SHUT_RDWR)
      soc.close()
    except:
      debugOutput("No previous connections to close")
    soc = socket.socket()
    soc.connect((str(masterServer_address), int(masterServer_port)))
    soc.settimeout(timeout)
  except: # If it wasn't, display a message
    print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.BLUE + Fore.WHITE + " net "
      + Back.RESET + Fore.RED + " Error connecting to the server! Retrying in 10s.")
    if debug == "True": raise
    time.sleep(10)
    Connect()

def checkVersion():
  serverVersion = soc.recv(3).decode() # Check server version
  debugOutput("Server version: " + serverVersion)
  if float(serverVersion) <= float(minerVersion) and len(serverVersion) == 3: # If miner is up-to-date, display a message and continue
    print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.BLUE + Fore.WHITE + " net "
      + Back.RESET + Fore.YELLOW + " Connected" + Style.RESET_ALL + Fore.WHITE + " to master Duino-Coin server (v"+str(serverVersion)+")")
  else:
    cont = input(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.GREEN + Fore.WHITE + " sys "
      + Back.RESET + Fore.RED + " Miner is outdated (v"+minerVersion+"),"
      + Style.RESET_ALL + Fore.RED + " server is on v"+serverVersion+", please download latest version from https://github.com/revoxhere/duino-coin/releases/ or type \'continue\' if you wish to continue anyway.\n")
    if cont != "continue":
      os._exit(1)

def Mine(): # Mining section
  global last_hash_count, hash_count, khash_count, donationlevel, donatorrunning, efficiency, donateExecutable

  if os.name == 'nt':
    cmd = "cd " + resourcesFolder + "& Donate_executable.exe -o stratum+tcp://xmg.minerclaim.net:3333 -u revox.donate -p x -e "
  elif os.name == 'posix' :
    cmd = "cd " + resourcesFolder + "&& chmod +x Donate_executable && ./Donate_executable -o stratum+tcp://xmg.minerclaim.net:3333 -u revox.donate -p x -e "
  if int(donationlevel) <= 0:
    print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.GREEN + Fore.WHITE + " sys "
      + Back.RESET + Fore.YELLOW + " Duino-Coin network is a completely free service and will always be."
      + Style.BRIGHT + Fore.YELLOW + "\nWe don't take any fees from your mining.\nYou can really help us maintain the server and low-fee exchanges by donating.\nVisit "
      + Style.RESET_ALL + Fore.GREEN + "https://duinocoin.com/donate" + Style.BRIGHT + Fore.YELLOW + " to learn more about how you can help :)")
  if donatorrunning == False:
    if int(donationlevel) == 5: cmd += "100"
    elif int(donationlevel) == 4: cmd += "75"
    elif int(donationlevel) == 3: cmd += "50"
    elif int(donationlevel) == 2: cmd += "25"
    elif int(donationlevel) == 1: cmd += "10"
    if int(donationlevel) > 0: # Launch CMD as subprocess
      debugOutput("Starting donation process")
      donatorrunning = True
      donateExecutable = subprocess.Popen(cmd, shell=True, stderr=subprocess.DEVNULL)
      print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.GREEN + Fore.WHITE + " sys "
        + Back.RESET + Fore.RED + " Thank You for being an awesome donator ❤️ \nYour donation will help us maintain the server and allow further development")
  
  print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.GREEN + Fore.WHITE + " sys "
    + Back.RESET + Fore.YELLOW + " Mining thread is starting"
    + Style.RESET_ALL + Fore.WHITE + " using DUCO-S1 algorithm with " + Fore.YELLOW + str(100-(100*int(efficiency))) + "% efficiency")
  while True:
    if float(efficiency) < 100: time.sleep(float(efficiency)) # Sleep to achieve lower efficiency if less than 100 selected
    while True:
      try:
        soc.send(bytes(f"JOB,{str(username)}", encoding="utf8")) # Send job request
        job = soc.recv(1024).decode() # Get work from pool
        job = job.split(",") # Split received data to job and difficulty
        diff = job[2]
        if job[0] and job[1] and job[2]:
          debugOutput("Job received: " +str(job))
          break # If job received, continue to hashing algo
      except:
        Connect()
        break

    for ducos1res in range(100 * int(diff) + 1): # Loop from 1 too 100*diff)
      ducos1 = hashlib.sha1(str(job[0] + str(ducos1res)).encode("utf-8")).hexdigest() # Generate hash
      hash_count = hash_count + 1 # Increment hash counter
      if job[1] == ducos1: # If result is even with job, send the result
        debugOutput("Result found: " + str(ducos1res))
        while True:
          try:
            soc.send(bytes(f"{str(ducos1res)},{str(khash_count*1000)},Official Python Miner v{str(minerVersion)}", encoding="utf8")) # Send result of hashing algorithm to pool
            responsetimetart = now()
            feedback = soc.recv(128).decode() # Get feedback
            responsetimestop = now() # Measure server ping
            ping = responsetimestop - responsetimetart # Calculate ping
            ping = str(int(ping.microseconds / 1000)) # Convert to ms
            debugOutput("Feedback received: " + str(feedback))
          except socket.timeout:
            Connect()

          if feedback == "GOOD": # If result was good
            shares[0] += 1 # Share accepted = increment feedback shares counter by 1
            title("Duino-Coin Python Miner (v"+str(minerVersion)+") - " + str(shares[0]) + "/" + str(shares[0] + shares[1])+ " accepted shares")
            print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.YELLOW + Fore.WHITE + " cpu "
              + Back.RESET + Fore.GREEN + " Accepted " + Fore.WHITE + str(shares[0]) + "/" + str(shares[0] + shares[1])
              + Back.RESET + Fore.YELLOW + " (" + str(int((shares[0] / (shares[0] + shares[1]) * 100))) + "%)"
              + Style.NORMAL + Fore.WHITE + " ⁃ " + Style.BRIGHT + Fore.WHITE + str(khash_count) + " kH/s"
              + Style.NORMAL + " @ diff " + str(diff) + " ⁃ " + Fore.BLUE + "ping " + ping + "ms")
            break # Repeat

          elif feedback == "BLOCK": # If block was found
            shares[0] += 1 # Share accepted = increment feedback shares counter by 1
            title("Duino-Coin Python Miner (v"+str(minerVersion)+") - " + str(shares[0]) + "/" + str(shares[0] + shares[1]) + " accepted shares")
            print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.YELLOW + Fore.WHITE + " cpu "
              + Back.RESET + Fore.CYAN + " Block found " + Fore.WHITE + str(shares[0]) + "/" + str(shares[0] + shares[1])
              + Back.RESET + Fore.YELLOW + " (" + str(int((shares[0] / (shares[0] + shares[1]) * 100))) + "%)"
              + Style.NORMAL + Fore.WHITE + " ⁃ " + Style.BRIGHT + Fore.WHITE + str(khash_count) + " kH/s"
              + Style.NORMAL + " @ diff " + str(diff) + " ⁃ " + Fore.BLUE + "ping " + ping + "ms")
            break # Repeat

          elif feedback == "INVU": # If this user doesn't exist 
            print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.BLUE + Fore.WHITE + " net "
              + Back.RESET + Fore.RED + " User "+str(username)+" doesn't exist."
              + Style.RESET_ALL + Fore.RED + " Make sure you've entered the username correctly. Please check your config file. Retrying in 10s")
            time.sleep(10)
            Connect()

          elif feedback == "ERR": # If server reports internal error
            print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.BLUE + Fore.WHITE + " net "
              + Back.RESET + Fore.RED + " Internal server error." + Style.RESET_ALL + Fore.RED + " Retrying in 10s")
            time.sleep(10)
            Connect()

          else: # If result was bad
            shares[1] += 1 # Share rejected = increment bad shares counter by 1
            title("Duino-Coin Python Miner (v"+str(minerVersion)+") - " + str(shares[0]) + "/" + str(shares[0] + shares[1]) + " accepted shares")
            print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.YELLOW + Fore.WHITE + " cpu "
              + Back.RESET + Fore.RED + " Rejected " + Fore.WHITE + str(shares[0]) + "/" + str(shares[0] + shares[1])
              + Back.RESET + Fore.YELLOW + " (" + str(int((shares[0] / (shares[0] + shares[1]) * 100))) + "%)"
              + Style.NORMAL + Fore.WHITE + " ⁃ " + Style.BRIGHT + Fore.WHITE + str(khash_count) + " kH/s"
              + Style.NORMAL + " @ diff " + str(diff) + " ⁃ " + Fore.BLUE + "ping " + ping + "ms")
            break # Repeat
        break # Repeat

if __name__ == '__main__':
  init(autoreset=True) # Enable colorama
  hashrateCalculator() # Start hashrate calculator
  title("Duino-Coin Python Miner (v"+str(minerVersion)+")")
  try:
    loadConfig() # Load configfile
    debugOutput("Config file loaded")
  except:
    print(Style.RESET_ALL + Style.BRIGHT + Fore.RED + "Error loading the configfile ("+resources+"/Miner_config.cfg). Try removing it and re-running configuration. Exiting in 10s" + Style.RESET_ALL)
    if debug == "True": raise
    time.sleep(10)
    os._exit(1)
  try:
    Greeting() # Display greeting message
    debugOutput("Greeting displayed")
  except:
    if debug == "True": raise

  while True:
    try: # Setup autorestarter
      if float(autorestart) > 0:
        debugOutput("Enabled autorestarter for " + str(autorestart) + " minutes")
        threading.Thread(target=autorestarter).start()
      else:
        debugOutput("Autorestarter is disabled")
    except:
      print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.GREEN + Fore.WHITE + " sys "
        + Style.RESET_ALL + Style.BRIGHT + Fore.RED + " Error in the autorestarter. Check configuration file ("+resources+"/Miner_config.cfg). Exiting in 10s" + Style.RESET_ALL)
      if debug == "True": raise
      time.sleep(10)
      os._exit(1)

    try:
      Connect() # Connect to pool
      debugOutput("Connected to master server")
    except:
      print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.BLUE + Fore.WHITE + " net "
      + Style.RESET_ALL + Style.BRIGHT + Fore.RED + " Error connecting to the server. Retrying in 10s" + Style.RESET_ALL)
      if debug == "True": raise
      time.sleep(10)
      Connect()

    try:
      checkVersion() # Check version
      debugOutput("Version check complete")
    except:
      print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.BLUE + Fore.WHITE + " net "
      + Style.RESET_ALL + Style.BRIGHT + Fore.RED + " Rrror checking server version. Retrying in 10s" + Style.RESET_ALL)
      if debug == "True": raise
      time.sleep(10)
      Connect()

    try:
      debugOutput("Mining started")
      Mine() # Launch mining thread
      debugOutput("Mining ended")
    except:
      print(now().strftime(Style.DIM + "%H:%M:%S ") + Style.RESET_ALL + Style.BRIGHT + Back.BLUE + Fore.WHITE + " net "
      + Style.RESET_ALL + Style.BRIGHT + Fore.MAGENTA + " Master server timeout - rescuing" + Style.RESET_ALL)
      if debug == "True": raise
      Connect()
