import os 
import requests
import shutil
import json
from pathlib import Path



def replace_by_default(output_path, file_path, filename):
    # URL not found, get default image to replace
    not_found_image_filename = output_path + f'images\\notfound.jpg'
    try:
        #create /images if not exists
        if not os.path.exists(output_path + "\images"):
            create_image_files(output_path)

        # Copy default "not found" image and name it with contact id as file name
        shutil.copy2(not_found_image_filename, file_path +
                        '\\' + filename + '.jpg')
    except IOError as error:
        print(error)


def check_internet_connection(host='http://google.com'):
    try:
        req = requests.get(host)  # Python 3.x
        return True
    except:
        return False


def extract(output_path, file_path, url, filename, filetype):
    if (not check_internet_connection()):
        print("Warning: Internet connection is required for images display")
        exit()
    try:
        # Create diretory if not exists
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        # Make request
        req = requests.get(url)
        if req.status_code == requests.codes.ok:
            # Create image file with contact id as file name
            filename = file_path + "\\" + filename + filetype
            try:
                f = open(filename, 'wb+')
                f.write(req.content)
                f.close()
            except IOError as error:
                print(error)
        else:
            replace_by_default(output_path, file_path, filename)
    except IOError as error:
        print(error)


def get_filetype(file_url):
    strSplit = file_url.split('?')
    strLen = len(strSplit[0])
    periodIndex = strLen - 1
    while (strSplit[0][periodIndex].find('.') == -1):
        periodIndex = periodIndex -1
        if (periodIndex < 0):
            break
    filetype = strSplit[0][periodIndex:strLen]
    return filetype


def get_filename_from_url(url):
    strSplit = url.split('/')
    splitCount = len(strSplit)
    strFilename = strSplit[splitCount-1]
    strLen = len(strFilename)
    periodIndex = 0
    while (strFilename[periodIndex].find('.') == -1):
        periodIndex = periodIndex + 1
        if (strFilename[periodIndex].find('?') != -1 or periodIndex == strLen-1):
            break
    filename = strFilename[0:periodIndex-1]
    return filename


def create_index_html(output_path):
    try:
        template_index_path = os.path.join(os.path.dirname(__file__), r'..\templates\\template_index.html')
        output_path = os.path.expandvars(output_path)
        dst_path = output_path +  r'\report\report.html'
        shutil.copy2(template_index_path, dst_path)
    except OSError as error:
        print(error)


def create_js_css(output_path):
    output_path = os.path.expandvars(output_path) + r'\report'
    try:
        if not os.path.exists(output_path + "\js"):
            os.makedirs(output_path + "\js")
        js_path = os.path.join(os.path.dirname(__file__), r'..\templates\js\\')
        js_files = os.listdir(js_path)
        for filename in js_files:
            shutil.copy2(os.path.join(js_path, filename), output_path + "\js")

        if not os.path.exists(output_path + "\css"):
            os.makedirs(output_path + "\css")
        js_path = os.path.join(os.path.dirname(__file__), r'..\templates\css\\')
        js_files = os.listdir(js_path)
        for filename in js_files:
            shutil.copy2(os.path.join(js_path, filename), output_path + "\css")
    except OSError as error:
        print(error)


def create_image_files(output_path):
    try:
        #create /images if not exists
        if not os.path.exists(output_path + "\images"):
            os.makedirs(output_path + "\images")

            images_dir = os.path.join(os.path.dirname(__file__), r'..\templates\images\\')
            images = os.listdir(images_dir)
            for image in images:
                shutil.copy2(images_dir + image,
                            output_path + "\images")

    except IOError as error:
        print(error)


def create_web_files(output_path):
    create_image_files(output_path)
    create_index_html(output_path)
    create_js_css(output_path)


def get_db_path(input_file_path):
    try:
        if os.path.exists(input_file_path):
            auth_id = 0
            f_data = open(input_file_path + 'data', 'r')
            data = json.load(f_data)
            for item in data:
                txt = item.split(":")
                auth_id = txt[1]
                break
            db_file_name = "msys_" + auth_id + ".db"
            db_path = input_file_path + db_file_name
            return db_path
        else:
            raise IOError("Error: File not found on given path")
    except IOError as error:
        print(error)
        exit()


def get_input_file_path(user_path):
    path = os.path.expandvars(user_path)
    return path + f'\AppData\Local\Packages\Facebook.FacebookMessenger_8xx8rvfyw5nnt\LocalState\\'


def get_output_file_path(path):
    path = os.path.expandvars(path)
    new_path = path + "\\report\\"
    try:
        if not os.path.exists(path):
            raise IOError("Error: Given destination output path not found :" + path)
        if not os.path.exists(new_path):
            os.makedirs(new_path)
        return new_path
    except IOError as error:
        print(error)
        exit()
    