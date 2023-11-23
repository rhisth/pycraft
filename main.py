import zipfile
import json
import requests
import os
from os.path import exists

minecraft_path = "./minecraft"
version_manifest_path = minecraft_path + "/version_manifest.json"
ast_dir = minecraft_path + "/assets"
obj_dir = ast_dir + "/objects"
ind_dir = ast_dir + "/indexes"
nat_dir = minecraft_path + "/natives"
lib_dir = minecraft_path + "/libraries"
ver_dir = minecraft_path + "/versions"

os_name = "windows"
arch = "64"

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def download(url, path):
    with open(path, 'wb') as file:
        file.write(requests.get(url).content)

def get_version(id):
    with open(version_manifest_path, "r") as file:
        versions = json.loads(file.read())["versions"]
    for version in versions:
        if version["id"] == id:
            url = version["url"]
            return url
    return False

def check_files():
    check_dir(ver_dir)
    check_dir(lib_dir)
    check_dir(nat_dir)
    check_dir(obj_dir)
    check_dir(ind_dir)
    if not exists(version_manifest_path):
        download("https://launchermeta.mojang.com/mc/game/version_manifest.json", version_manifest_path)

def check_dir(path):
    if not exists(path):
        os.makedirs(path)

def check_download(path, url):
    if not exists(path):
        download(url, path)

def check_rules(rules):
    result = False
    for rule in rules:
        action = rule["action"]
        if action == "allow":
            if not "os" in rule:
                result = True
            else:
                if os_name == rule["os"]:
                    result = True
        if action == "disallow" and "os" in rule:
            if os_name == rule["os"]:
                result = False
                break
    return result

def download_resources(index):
    for object in index["objects"]:
        hash = objects[object]["hash"]
        folder = hash[:2]
        path = f"{obj_dir}/{folder}/{hash}"
        if not exists(path):
            check_dir(f"{obj_dir}/{folder}")
            download(f"https://resources.download.minecraft.net/{folder}/{hash}", path)

def download_libraries(libraries):
    for library in libraries:
        if "rules" in library and not "natives" in library:
            if not check_rules(library["rules"]):
                continue
        if "natives" in library:
            if os_name in library["natives"]:
                key = library['natives'][os_name].replace("${arch}", arch)
                lib = library['downloads']['classifiers'][key]
            else:
                continue
        else:
            lib = library["downloads"]["artifact"]
        path = f"{lib_dir}/{lib['path']}"
        if not exists(path):
            check_dir(os.path.dirname(path))
            download(lib["url"], path)

def download_version(id):
    url = get_version(id)
    if not url:
        return False
    answer = requests.get(url).json()
    check_dir(f"{ver_dir}/{id}")
    check_download(f"{ver_dir}/{id}/{id}.json", url)
    check_download(f"{ind_dir}/{answer['assetIndex']['id']}.json", answer["assetIndex"]["url"])
    download_libraries(answer["libraries"])
    download_resources(requests.get(answer["assetIndex"]["url"]).json())
    check_download(f"{ver_dir}/{id}/{id}.jar", answer["downloads"]["client"]["url"])
    return True

def setup_natives(id):
    with open(f"{ver_dir}/{id}/{id}.json", "r") as file:
        libraries = json.loads(file.read())["libraries"]
    natives = [library for library in libraries if "natives" in library]
    check_dir(f"{nat_dir}/{id}")
    for native in natives:
        if os_name in native["natives"]:
            key = native['natives'][os_name].replace("${arch}", arch)
            path = f"{lib_dir}/{native['downloads']['classifiers'][key]['path']}"
            with zipfile.ZipFile(path, "r") as zip_ref:
                zip_ref.extractall(f"{nat_dir}/{id}")

def get_libraries(libraries):
    liblist = []
    for library in libraries:
        if not "natives" in library:
            if "rules" in library:
                if not check_rules(library["rules"]):
                    continue
            liblist.append(f'{lib_dir}/{library["downloads"]["artifact"]["path"]}')
    return liblist

def get_arguments(info, nickname):
    if not "minecraftArguments" in info:
        args = " ".join(arg for arg in info["arguments"]["game"] if isinstance(arg, str))
    else:
        args = info["minecraftArguments"]
    id = info["id"]
    uuid = "null"
    access_token = "null"
    user_type = "msa"
    version_type = info["type"]
    user_properties = "{}"
    replacing = {"${auth_player_name}": nickname, "${version_name}": id, "${game_directory}": minecraft_path, "${assets_root}": ast_dir, "${assets_index_name}": info["assetIndex"]["id"], "${auth_uuid}": uuid, "${auth_access_token}": access_token, "${user_type}": user_type, "${version_type}": version_type, "${user_properties}": user_properties}
    for arg in replacing:
        args = args.replace(arg, replacing[arg])
    return args

def start_version(id, nickname):
    with open(f"minecraft/versions/{id}/{id}.json", "r") as file:
        version_info = json.loads(file.read())
    cp = ";".join(get_libraries(version_info["libraries"]))
    mainclass = version_info["mainClass"]
    args = get_arguments(version_info, nickname)
    command = f'java -Dos.name="Windows 10" -Dos.version=10.0 -Djava.library.path={nat_dir}/{id} -Dminecraft.launcher.brand=minecraft-launcher -Dminecraft.launcher.version=2.7.12 -cp {cp};{minecraft_path}/versions/{id}/{id}.jar -XX:HeapDumpPath=MojangTricksIntelDriversForPerformance_javaw.exe_minecraft.exe.heapdump -Xmx2G -XX:+UnlockExperimentalVMOptions -XX:+UseG1GC -XX:G1NewSizePercent=20 -XX:G1ReservePercent=20 -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=32M -Dfml.ignoreInvalidMinecraftCertificates=true -Dfml.ignorePatchDiscrepancies=true -Djava.net.preferIPv4Stack=true -Dminecraft.applet.TargetDirectory={minecraft_path} {mainclass} {args}'
    setup_natives(id)
    print(command)
    os.system(command)

commands = {"clear": "clear", "download": "download_version", "start": "start_version"}
def process_command(text):
    split = text.split(" ", 1)
    command = split[0]
    if not command in commands:
        print("Неизвестная команда.")
        return
    if len(split) > 1:
        args = ", ".join(split[-1].split(","))
    else:
        args = ""
    try:
        exec(f"{commands[command]}({args})")
    except Exception as ex:
        print(ex)

def main():
    while True:
        check_files()
        process_command(input("Команда: "))

if __name__ == "__main__":
    main()
