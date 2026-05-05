import requests
import zipfile as zf
import py7zr
from os import mkdir
from os.path import isdir, isfile
from shutil import copytree, rmtree

#Limitations:
#No discord files, BCJ2 filter is not supported by py7zr

modUpdaterVersion = "1.2.2"

def setup() -> tuple[list, bool]:
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
    mr = requests.get("https://raw.githubusercontent.com/tannerreal/stdmodupd/refs/heads/main/modlistv2.json") #Replace me i you want to use a different modlist, note: modlists always start with 1, if you want to download version 1 of modlist, put a zero in the .modlistVer file

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
        open(".modlistVer", "w").write(str(modlistVer))
        if not isdir("./update"): #Easier to make the directory each time rather than clear files one by one on cleanup
            mkdir("./update")
            print(" >No update folder found")

    print("")
    return downloadList, modsUpToDate

def generateCache(bundledFiles: list): #We need to generate cache because downloading bundles from server takes too long (300kbps upload limit)
    progress = 0
    print(" >Generating cache...")
    for f in bundledFiles:
        progress += 1
        print(" >["+str(progress)+"/"+str(len(bundledFiles))+"]")
        copytree("./"+f, ".\\SPT\\user\\cache", dirs_exist_ok=True)

def extract(bundledFiles: list, file: str) -> list: #Takes the bundledfiles, processes them, extracts them, returns bundledfiles
    if file.find(".7z") > -1:
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
            #print(" >Broken path(SPT): "+bork2)
        if f.find("BepInEx/plugins") > 0:
            bork2 = f[0:f.find("BepInEx/plugins")-1]
            #print(" >Broken path(BepInEx): "+bork2)

        if bork2: 
            found = False
            for fx in fixlist:
                if fx == bork2: found = True
            if not found: #No need to append the same path that needs fixing more than once
                print(" >Found broken path: "+bork2)
                fixlist.append(bork2)

        if f.find("/bundles/") > -1 and f.find("SPT/user/mods") > -1:
            bundlePath=f[f.find("SPT/user/"):f.find("/bundles/")+8] #this also fixes the path by finding where spt folder is in case its broken
            
            found = False
            for bf in bundledFiles:
                if bf == bundlePath:
                    found = True
            if not found:
                bundledFiles.append(bundlePath)

            print(" >Found bundles: "+bundlePath)
    print(" >Extracting "+file+"...")
    if file.find(".7z") > -1:
        py7zr.SevenZipFile(file).extractall()
    elif file.find(".zip") > -1:
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

def getFile(url: str, name: str) -> bool: #Download function,,,,
    fname = ".\\update\\"+name
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0"} #I wish i didn't have to fake user agent for forge, if any1 from forge sees this, sorry!

    with requests.get(url, stream=True, headers=ua) as r:
        r.raise_for_status()
        if r.status_code == 200:
            with open(fname, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        else:
            print(" >ERROR: download failed for '"+url+"' :: '"+name+"' Status code: "+str(r.status_code))
            return False

    return True

def getListInstance(name: str, downloadList: list):
    for mod in downloadList:
        if mod["name"] == name:
            return (mod, downloadList.index(mod))
    return ("", 0)

def main():
    downloadList, modsUpToDate = setup()
    bundledFiles = []

    if not modsUpToDate:
        print(" >Mods out of date")
        for mod in downloadList:
            fname = mod["name"]+"."+mod["format"]
            print(" >Downloading: "+mod["url"]+" :: "+fname)

            if getFile(mod["url"], fname): #if the download succeeded, extract files and save list of bundles, else this will crash
                bundledFiles = extract(bundledFiles ,".\\update\\"+fname)

        print("")
        print(" >Done downloading mods")

        print(" >Cleaning up...")
        rmtree(".\\update")

        generateCache(bundledFiles)

    print("")
    print(" >Mods updated successfully, you can now close this window")
    exit = input()

if __name__ == "__main__":
    main()