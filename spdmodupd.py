import requests
import zipfile as zf
import py7zr
import subprocess
from os import mkdir
from os.path import isdir, isfile
from shutil import copytree, rmtree
from sys import stdout

#Limitations:
#No discord files

modUpdaterVersion = "1.3.2"
sevenZipDownloadLink = "https://github.com/ip7z/7zip/releases/download/26.01/7zr.exe"
modListLink = "https://raw.githubusercontent.com/tannerreal/stdmodupd/refs/heads/main/modlistv2.json" #Replace me i you want to use a different modlist, note: modlists always start with 1, if you want to download version 1 of modlist, put a zero in the .modlistVer file


def setup() -> tuple[list, bool, int]:
    print(" >Updater version: "+modUpdaterVersion)
    print("")

    downloadList = []
    modsUpToDate = True
    
    if isfile(".modlistVer"): 
        c = open(".modlistVer").read()
        if c:
            modlistVer = int(c)
        else:
            modlistVer = 1
            open(".modlistVer", "w").write("1")
    else:
        modlistVer = 1
        open(".modlistVer", "w").write("1")

    print(" >Downloading modlist...")
    mr = requests.get(modListLink) 
    if mr and mr.status_code == 200:
        modlist = mr.json()
    else:
        raise Exception(" >ERROR: no modlist, status code: "+str(mr.status_code))
    
    print(" >Parsing modlist...")
    for list in modlist:
        if modlist[str(list)]["version"] > modlistVer:
            modsUpToDate = False
            modlistVer += 1
            for list1 in modlist[str(list)]["list"]:
                checkMod, idx = getListInstance(list1["name"], downloadList)
                if checkMod: #we check the modname if it already exists, if we find a mod that has an older version from a previous version of modlist, replace that index with a newer download of the mod
                    if checkMod["modver"] < list1["modver"]:
                        downloadList[idx] = list1
                    else:
                        downloadList.append(list1)
                else:
                    downloadList.append(list1)

    if modsUpToDate:
        print(" >Modlist is up to date")
    else:
        if not isdir("./update"): #Easier to make the directory each time rather than clear files one by one on cleanup
            mkdir("./update")
            print(" >No update folder found")

    print("")
    return downloadList, modsUpToDate, modlistVer

def generateCache(bundledFiles: list) -> None: #We need to generate cache because downloading bundles from server takes too long (300kbps upload limit)
    progress = 0
    print(" >Generating cache...")
    for f in bundledFiles:
        progress += 1
        print(" >["+str(progress)+"/"+str(len(bundledFiles))+"] "+f)
        copytree("./"+f, ".\\SPT\\user\\cache", dirs_exist_ok=True)

def check7z() -> None:
    if not isfile("7z.exe"):
        print(" >Warning: 7z not found, downloading...")
        if not getFile(sevenZipDownloadLink, "7z.exe", True):
            raise Exception(" >ERROR: unable to download 7z")

def subGetNames(file: str) -> list:
    check7z()
    cmd = ["7z", "l", "-ba", file]
    sub = subprocess.run(cmd, capture_output=True, text=True) #potentially vulnerable if you name the file some wackass shit
    subsplit = sub.stdout
    paths = []
    while subsplit:
        idx = subsplit.find("\n")
        paths.append(subsplit[53:idx].replace("\\", "/")) #with the -ba switch, paths are guranteed to start at characher 53, form there we can just find the nearest newline, thanks https://stackoverflow.com/a/68070379
        subsplit=subsplit[idx+1:len(subsplit)]
    return paths

def subExtract(file: str) -> int:
    check7z()
    cmd = ["7z", "x", "-ba", file]
    sub = subprocess.run(cmd, capture_output=True, text=True)

    return sub.returncode

def extract(bundledFiles: list, file: str) -> list: #Takes the bundledfiles, processes them, extracts them, returns bundledfiles
    if file.find(".7z") > -1:
        if "BCJ2*" in py7zr.SevenZipFile(file).archiveinfo().method_names: #for now, just skip the file, in the future, implement a way to unzip it maybe with subprocessing 7z in cmd
            #print(" ===!!!=== ")
            print(" >Warning: unsupported format BCJ2 for archive: '"+file+"', using a 7z subprocess!") #would be cool if liblzma or py7zr would implement it but oh well its only a majorly public format for one of the most popular archive formats
            #print(" ===!!!=== ")
            BCJ = True
            files = subGetNames(file) #adress me
        else:
            BCJ = False
            files = py7zr.SevenZipFile(file).getnames()
    elif file.find(".zip") > -1:
        files = zf.ZipFile(file).namelist()
    else:
        raise Exception(" >ERROR: unsupported file format for: "+file)

    fixlist = []
    for f in files:

        bork2 = ""
        if f.find("SPT/user") > 0: #If the spt or bepinex folders are not on index 0 that means they are farther down the directory list, needs fixing
            bork2 = f[0:f.find("SPT/user")-1]
        if f.find("BepInEx/plugins") > 0:
            bork2 = f[0:f.find("BepInEx/plugins")-1]

        if bork2: 
            found = False
            for fx in fixlist:
                if fx == bork2: found = True
            if not found: #No need to append the same path that needs fixing more than once
                print(" >Found broken path: "+bork2)
                fixlist.append(bork2)

        if f.find("/bundles") > -1 and f.find("SPT/user/mods") > -1:
            bundlePath=f[f.find("SPT/user/"):f.find("/bundles")+8] #this also fixes the path by finding where spt folder is in case its broken
            
            found = False
            for bf in bundledFiles:
                if bf == bundlePath:
                    found = True
            if not found:
                print(" >Found bundles: "+bundlePath)
                bundledFiles.append(bundlePath)

    print(" >Extracting: "+file+"...")
    if file.find(".7z") > -1:
        if BCJ:
            print("")
            stat = subExtract(file)
            if not stat == 0:
                print(" >ERROR: failed to extract a BCJ2 archive using a 7z subprocess, return code: "+str(stat))
        else:
            print("")
            py7zr.SevenZipFile(file).extractall()
    elif file.find(".zip") > -1:
        print("")
        zf.ZipFile(file).extractall()
    else:
        raise Exception(" >ERROR: unsupported file format for: "+file)

    for f in fixlist:
        f = f.replace("/", "\\") #i hate paths
        print(" >Fix path for: "+f)
        fsplit = f.split("\\")

        copytree(".\\"+f, ".", dirs_exist_ok=True) #fix for mods that don't ship spt/bepinex in the root of the zip
        rmtree(".\\"+fsplit[0])

    return bundledFiles

def printProgress(p: int, pmax: int) -> None:
    string = " >["+str( round(p/pmax*100) )+"%] ("+str(p)+"/"+str(pmax)+")"
    clear = ""
    for _ in range(0, len(string)):
        clear+="\b"
    stdout.write(clear)
    stdout.write(string)
    stdout.flush()

def getFile(url: str, name: str, direct: bool = False) -> tuple[bool, int]: #Download function,,,,
    if not direct:
        fname = ".\\update\\"+name
    else:
        fname = name

    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0"} #I wish i didn't have to fake user agent for forge, if any1 from forge sees this, sorry!

    if isfile(fname):
        return True, 1
    
    sreq = requests.get(url, stream=True, headers=ua).headers['Content-length']
    if sreq:
        size = int(sreq)
    else:
        size = 0
    current = 0

    with requests.get(url, stream=True, headers=ua) as r:
        if r.status_code == 200:
            r.raise_for_status()
            with open(fname, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    current+=8192
                    f.write(chunk)
                    if current > size: current = size #the last chunk is not guranteed to be of that size
                    printProgress(current, size)
        else:
            print(" >ERROR: download failed for '"+url+"' :: '"+name+"' Status code: "+str(r.status_code)) 
            print("")
            return False, 1

    print("")
    return True, 0

def getListInstance(name: str, downloadList: list):
    for mod in downloadList:
        if mod["name"] == name:
            return (mod, downloadList.index(mod))
    return ("", 0)

def main():
    downloadList, modsUpToDate, modlistVer = setup()
    bundledFiles = []

    if not modsUpToDate:
        print(" >Mods out of date")
        for mod in downloadList:
            fname = mod["name"]+"."+mod["format"]
            print(" >["+str(downloadList.index(mod)+1)+"/"+str(len(downloadList))+"]"+" Downloading: "+mod["url"]+" :: "+fname+"...")

            getB, getI = getFile(mod["url"], fname)
            if getB: #if the download succeeded, extract files and save list of bundles, else this will crash
                bundledFiles = extract(bundledFiles ,".\\update\\"+fname)

        print("")
        print(" >Done downloading mods")

        print(" >Cleaning up...")
        rmtree(".\\update")

        generateCache(bundledFiles)

        open(".modlistVer", "w").write(str(modlistVer))

    print("")
    print(" >Mods updated successfully, you can now close this window")
    exit = input()

if __name__ == "__main__":
    main()