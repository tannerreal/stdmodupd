import requests
import zipfile as zf
import py7zr
from os import mkdir
from os.path import isdir, isfile
from shutil import copytree, rmtree

#Limitations:
#No discord files, BCJ2 filter is not supported by py7zr

modUpdaterVersion = "1.2.0"

def setup(downloadList: list, modsUpToDate: bool) -> tuple[list, bool]:
    print(" >Updater version: "+modUpdaterVersion)
    print("")
    
    if isfile(".modlistVer"): 
        c = open(".modlistVer").read()
        if c:
            modlistVer = int(c)
        else:
            modlistVer = 1
            open(".modlistVer", "w").write("0")
    else:
        modlistVer = 1
        open(".modlistVer", "w").write("0")

    print(" >Downloading modlist...")
    modlist = requests.get("https://raw.githubusercontent.com/tannerreal/stdmodupd/refs/heads/main/modlistv2.json").json()
    
    if not modlist:
        raise Exception(" >ERROR: no modlist")
    
    print(" >Parsing modlist...")
    for list in modlist:
        if modlist[str(list)]["version"] > modlistVer:
            modsUpToDate = False
            modlistVer += 1
            for list1 in modlist[str(list)]["list"]:
                checkMod, idx = getListInstance(list1["name"], downloadList)
                if checkMod:
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
        if not isdir("./update"):
            mkdir("./update")
            print(" >No update folder found")

    return downloadList, modsUpToDate
    print("")

def generateCache(bundledFiles: list):
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
        if f.find("/bundles/") > -1:
            bundlePath = ""

            split = f.split("/")
            if not split[0] == "SPT":
                rangeStart = 1
                found = False
                for f in fixlist:
                    if f == split[0]:
                        found = True
                if not found:
                    fixlist.append(split[0])
            else:
                rangeStart = 0
            
            for s in range(rangeStart, len(split)):
                str = split[s]
                bundlePath += "/"+str
                if str == "bundles":
                    break

            found = False
            for bf in bundledFiles:
                if bf == bundlePath:
                    found = True
            if not found:
                bundledFiles.append(bundlePath)
    print(" >Extracting: "+file+"...")
    if file.find(".7z") > -1:
        py7zr.SevenZipFile(file).extractall()
    elif file.find(".zip") > -1:
        zf.ZipFile(file).extractall()
    else:
        raise Exception(" >ERROR: unsupported file format for: "+file)

    for f in fixlist:
        print(f)
        copytree(".\\"+f, ".", dirs_exist_ok=True) #fix for mods that don't ship spt/bepinex in the root of the zip
        rmtree(".\\"+f)

    return bundledFiles

def getFile(url: str, name: str):
    fname = ".\\update\\"+name
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0"}

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
    modsUpToDate = True
    downloadList = []
    downloadList, modsUpToDate = setup(downloadList, modsUpToDate)
    #modlistVer = 1
    bundledFiles = []

    if not modsUpToDate:
        print(" >Mods out of date")
        for mod in downloadList:
            fname = mod["name"]+"."+mod["format"]
            print(" >Downloading: "+mod["url"]+" :: "+fname)

            if getFile(mod["url"], fname):
                bundledFiles = extract(bundledFiles ,".\\update\\"+fname)

        print("")
        print(" >Done downloading mods")

        print(" >Cleaning up...")
        rmtree(".\\update")

        generateCache(bundledFiles)

    print(" >Mods updated successfully, you can now close this window")
    exit = input()

if __name__ == "__main__":
    main()