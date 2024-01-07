import os
import vdf
import time
import shutil
import winreg
import argparse
import requests
import traceback
import subprocess
import requests
import yaml
from tkinter import messagebox
from pathlib import Path
from multiprocessing.pool import ThreadPool
from multiprocessing.dummy import Pool, Lock
from requests.packages import urllib3

urllib3.disable_warnings()

print('当前版本12.0')
print('作者ikun、wxy1343')
print('声明:请勿用于商业用途,否则后果自负')
print('增加清单库: BlankTMing/ManifestAutoUpdate')

def gen_config():
    default_config = {
        'github_persoal_token': '' ,
        'github_persoal_token_example': 'Bearer your_github_persoal_token',
    }
    with open("./appsettings.yaml", "w", encoding="utf-8") as f:
        f.write(yaml.dump(default_config))
        f.close()
        if (not os.getenv('build')):
            print('首次启动或配置文件被删除，已创建默认配置文件')
        return gen_config
    
def load_config():
    if os.path.exists('appsettings.yaml'):
        with open('appsettings.yaml', 'r') as config_file:
            config = yaml.safe_load(config_file)
    else:
        gen_config()
        with open('appsettings.yaml', 'r') as config_file:
            config = yaml.safe_load(config_file)

    return config

lock = Lock()

def get(branch, path):
    url_list = [f'https://github.moeyy.xyz/https://raw.githubusercontent.com/lls7890/Repository/{branch}/{path}',
                f'https://github.moeyy.xyz/https://raw.githubusercontent.com/isKoi/Manifest-AutoUpdate/{branch}/{path}',
                f'https://githubapi.ikunshare.link/https://raw.githubusercontent.com/lls7890/Repository/{branch}/{path}',
                f'https://githubapi.ikunshare.link/https://raw.githubusercontent.com/isKoi/Manifest-AutoUpdate/{branch}/{path}',
                f'https://github.moeyy.xyz/https://raw.githubusercontent.com/qwq-xinkeng/awaqwqmain/{branch}/{path}',
                f'https://githubapi.ikunshare.link/https://raw.githubusercontent.com/qwq-xinkeng/awaqwqmain/{branch}/{path}',
                f'https://github.moeyy.xyz/https://raw.githubusercontent.com/liaofulong/Manifest-AutoUpdate/{branch}/{path}',
                f'https://githubapi.ikunshare.link/https://raw.githubusercontent.com/liaofulong/Manifest-AutoUpdate/{branch}/{path}',
                f'https://github.moeyy.xyz/https://raw.githubusercontent.com/BlankTMing/ManifestAutoUpdate/{branch}/{path}',
                f'https://githubapi.ikunshare.link/https://raw.githubusercontent.com/BlankTMing/ManifestAutoUpdate/{branch}/{path}']

    retry = 30
    while True:
        for url in url_list:
            try:
                r = requests.get(url,verify=False)
                if r.status_code == 200:
                    return r.content
            except requests.exceptions.ConnectionError:
                print(f'获取失败: {path}')
                retry -= 30
                if not retry:
                    print(f'超过最大重试次数: {path}')
                    raise


def get_manifest(branch, path, steam_path: Path, app_id=None):
    try:
        if path.endswith('.manifest'):
            depot_cache_path = steam_path / 'depotcache'
            with lock:
                if not depot_cache_path.exists():
                    depot_cache_path.mkdir(exist_ok=True)
            save_path = depot_cache_path / path
            if save_path.exists():
                with lock:
                    print(f'已存在清单: {path}')
                return
            content = get(branch, path)
            with lock:
                print(f'清单下载成功: {path}')
            with save_path.open('wb') as f:
                f.write(content)
        if path.endswith('.vdf') and path not in ['appinfo.vdf']:
            if path == 'config.vdf' or 'Key.vdf':
                content = get(branch, path)
            with lock:
                print(f'密钥下载成功: {path}')
            depots_config = vdf.loads(content.decode(encoding='utf-8'))
            if depotkey_merge(steam_path / 'config' / 'config.vdf', depots_config):
                print('合并config.vdf成功')
            if stool_add(
                    [(depot_id, '1', depots_config['depots'][depot_id]['DecryptionKey'])
                     for depot_id in depots_config['depots']]):
                print('导入steamtools成功')    
    except KeyboardInterrupt:
        raise
    except:
        traceback.print_exc()
        raise
    return True


def depotkey_merge(config_path, depots_config):
    if not config_path.exists():
        with lock:
            print('config.vdf不存在')
        return
    with open(config_path, encoding='utf-8') as f:
        config = vdf.load(f)
    software = config['InstallConfigStore']['Software']
    valve = software.get('Valve') or software.get('valve')
    steam = valve.get('Steam') or valve.get('steam')
    if 'depots' not in steam:
        steam['depots'] = {}
    steam['depots'].update(depots_config['depots'])
    with open(config_path, 'w', encoding='utf-8') as f:
        vdf.dump(config, f, pretty=True)
    return True

def stool_add(depot_list):
    steam_path = get_steam_path()
    lua_content = ""
    for depot_id, type_, depot_key in depot_list:
        lua_content += f"""addappid({depot_id}, {type_}, "{depot_key}")"""
    lua_filename = f"Onekey_unlock_{depot_id}.lua"
    lua_filepath = steam_path / "config" / "stplug-in" / lua_filename
    with open(lua_filepath, "w", encoding="utf-8") as lua_file:
        lua_file.write(lua_content)
    print(f"Lua文件生成成功: {lua_filepath}")
    print("steamtools导入成功")
    luapacka_path = steam_path / "config" / "stplug-in" / "luapacka.exe"
    subprocess.run([str(luapacka_path), str(lua_filepath)])
    os.remove(lua_filepath)
    return True

def get_steam_path():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam')
    steam_path = Path(winreg.QueryValueEx(key, 'SteamPath')[0])
    return steam_path

def main(app_id):
    config = load_config()
    github_persoal_token = config.get('github_persoal_token', '')
    headers = {'Authorization': f'{github_persoal_token}'}
    url = 'https://api.github.com/rate_limit'
    r = requests.get(url, headers=headers, verify=False)
    if r.status_code == 200:
        rate_limit = r.json()['rate']
        remaining_requests = rate_limit['remaining']
        reset_time = rate_limit['reset']
        reset_time_formatted = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(reset_time))
        print(f'剩余请求次数: {remaining_requests}')

        if remaining_requests == 0:
            print(f'GitHub API 请求数已用尽，将在 {reset_time_formatted} 重置')
            return True

    repos = [
        'https://api.github.com/repos/BlankTMing/ManifestAutoUpdate',
        'https://api.github.com/repos/lls7890/Repository',
        'https://api.github.com/repos/isKoi/Manifest-AutoUpdate',
        'https://api.github.com/repos/qwq-xinkeng/awaqwqmain',
        'https://api.github.com/repos/liaofulong/Manifest-AutoUpdate'
    ]

    latest_date = None
    selected_repo = None

    for repo_url in repos:
        url = f'{repo_url}/branches/{app_id}'

        try:
            r = requests.get(url, headers=headers, verify=False)
            if 'commit' in r.json():
                date = r.json()['commit']['commit']['author']['date']
                if latest_date is None or date > latest_date:
                    latest_date = date
                    selected_repo = repo_url
        except KeyboardInterrupt:
            exit()
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")

    if selected_repo:
        print(f'Selected Repo: {selected_repo}')
        url = f'{selected_repo}/branches/{app_id}'
        try:
            r = requests.get(url, verify=False)
            if 'commit' in r.json():
                branch = r.json()['name']
                url = r.json()['commit']['commit']['tree']['url']
                date = r.json()['commit']['commit']['author']['date']
                r = requests.get(url,verify=False)
                if 'tree' in r.json():
                    stool_add([(app_id, 1 , "None")])
                    result_list = []
                    with Pool(32) as pool:
                        pool: ThreadPool
                        for i in r.json()['tree']:
                            result_list.append(pool.apply_async(get_manifest, (branch, i['path'], get_steam_path(), app_id)))
                        try:
                            while pool._state == 'RUN':
                                if all([result.ready() for result in result_list]):
                                    break
                                time.sleep(0.1)
                        except KeyboardInterrupt:
                            with lock:
                                pool.terminate()
                            raise
                    if all([result.successful() for result in result_list]):
                        msg2 = messagebox.showwarning(title="警告", message="本软件为免费软件")
                        print(msg2)
                        print(f'清单最新更新时间:{date}')
                        print(f'入库成功: {app_id}')
                        print('重启steam生效')
                        return True
        except KeyboardInterrupt:
            exit()
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")

    print(f'入库失败: {app_id}')
    return False

def app(app_path):
    app_path = Path(app_path)
    if not app_path.is_dir():
        raise NotADirectoryError(app_path)
    steam_path = get_steam_path()
    app_id_list = list(filter(str.isdecimal, app_path.name.strip().split('-')))
    if app_id_list:
        app_id = app_id_list[0]
        stool_add([(app_id, 1, "None")])
    else:
        raise Exception('目录名称不是app_id')
    for file in app_path.iterdir():
        if file.is_file():
            if file.suffix == '.manifest':
                depot_cache_path = steam_path / 'depotcache'
                shutil.copy(file, depot_cache_path)
                print(f'导入清单成功: {file.name}')
            elif file.name == 'config.vdf' or 'Key.vdf':
                with file.open('r', encoding='utf-8') as f:
                    depots_config = vdf.loads(f.read())
                if depotkey_merge(steam_path / 'config' / 'config.vdf', depots_config):
                    print('合并config.vdf成功')
                if stool_add([(depot_id, '1',
                               depots_config['depots'][depot_id]['DecryptionKey']) for depot_id in
                              depots_config['depots']]):
                    print('导入steamtools成功')

parser = argparse.ArgumentParser()
parser.add_argument('-a', '--app-id')
parser.add_argument('-p', '--app-path')
args = parser.parse_args()
if __name__ == '__main__':
    try:
        load_config()
        if args.app_path:
            app(args.app_path)
        else:
            main(args.app_id or input('appid: '))
    except KeyboardInterrupt:
        exit()
    except:
        traceback.print_exc()
    if not args.app_id and not args.app_path:
        os.system('pause')