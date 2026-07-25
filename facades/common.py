import os
import logging
import sys
import yaml

app_location_for_commons = os.path.dirname(os.path.abspath(sys.argv[0]))

def file_path_resolver(file_path: str, is_parent: bool = False, sub_folder: str = None):
    if type(file_path).__name__ == 'StringIO':
        file_path.seek(0)
    else:
        path_before_file = os.path.dirname(file_path)
        file_name_only = os.path.basename(file_path)
        if os.path.isabs(path_before_file):
            dir_path = path_before_file
        else:
            dir_path = app_location_for_commons

        if is_parent: dir_path = os.path.dirname(dir_path)
        if sub_folder is not None: dir_path = os.path.join(dir_path, sub_folder)

        if path_before_file != '' and not os.path.isabs(path_before_file):
            dir_path = os.path.join(dir_path, path_before_file)

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        file_path = os.path.join(dir_path, file_name_only)
    return file_path

def os_f_read(file_name: str, is_parent: bool = False, sub_folder: str = None):
    file_path = file_path_resolver(file_name, is_parent=is_parent, sub_folder=sub_folder)
    with open(file_path, 'r') as file:
        if file_name.endswith('.yaml'):
            return yaml.safe_load(file)
        return file.read()

def os_f_write(file_name: str, content: str, is_parent: bool = False, sub_folder: str = None):
    file_path = file_path_resolver(file_name, is_parent=is_parent, sub_folder=sub_folder)
    with open(file_path, 'w') as file:
        if file_name.endswith('.yaml'):
            yaml.safe_dump(content, file, sort_keys=False, indent=2)
        else:
            file.write(content)

def logtofile(message, level: str = 'info', mode: str = 'a', path: str = None, file_name: str = 'logs.log'):
    # For mode 'a' to append and 'w' to overwrite the log file.
    if path is None:
        path = app_location_for_commons
    logfile_path = file_path_resolver(os.path.join(path, file_name))
    max_message_length = 1000 
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_handler = logging.FileHandler(logfile_path, mode=mode)
    console_handler = logging.StreamHandler(sys.stdout)
    message = str(message)
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[file_handler, console_handler]
    )
    if len(message) > max_message_length:
        message = message[:max_message_length] + '... [truncated]'
    if level == 'info':
        logging.info(message)
    elif level == 'warning':
        logging.warning(message)
    elif level == 'error':
        logging.error(message)

def map_lang(input: str, to: str = 'ISO_639_1'):
    # Map language name or code to the desired format (ISO_639_1, ISO_639_2 or name)
    this_location = os.path.dirname(os.path.abspath(__file__))
    lang_path = os.path.join(this_location, 'data', 'languages.yaml')
    langs = os_f_read(file_name=lang_path)

    if len(input) == 2:
        input_type = 'ISO_639_1'
    elif len(input) == 3:
        input_type = 'ISO_639_2'
    elif len(input) > 3:
        input_type = 'name'
    else:
        logtofile(f"Input '{input}' is too short to be a valid language code.", level='warning')
        return ''

    for lang, codes in langs.items():
        codes['name'] = lang
        if input.lower() in codes.get(input_type, '').lower():
            return codes.get(to, '')

if __name__ == "__main__":
    output_lang = 'lv'
    output_lang = map_lang(input = output_lang, to = 'ISO_639_2')
    print(output_lang)
    print(app_location_for_commons)
    # logtofile(f"Mapped language code: {output_lang}", level='info')
    
