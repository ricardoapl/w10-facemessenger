import os
import sys
import shutil
import csv
import json
import sqlite3
import copy
from pathlib import Path
# TODO: (orainha) Remove import requests
import requests

from bs4 import BeautifulSoup

from core.headers import fill_header

import utils.files as utils


# XXX (ricardoapl) Fix this non-pythonic mess!
CONVERSATIONS_TEMPLATE_FILENAME = os.path.join(os.path.dirname(__file__), r'..\templates\template_conversations.html')
MESSAGES_TEMPLATE_FILENAME = os.path.join(os.path.dirname(__file__), r'..\templates\template_messages.html')
NEW_FILE_PATH = ''
MESSAGES_PATH = ''
OUTPUT_PATH = ''
PATH = ''
DB_PATH = ''
MSG_FILES_FOLDER_NAME = ''

CONVERSATIONS_QUERRY = """
    SELECT
        c.profile_picture_url,
        c.name,
        c.profile_picture_large_url, 
        p.thread_key,
        p.contact_id,
        p.nickname
    FROM participants as p 
    JOIN contacts as c ON c.id = p.contact_id
"""

MESSAGES_PER_CONVERSATION_QUERRY = """
    SELECT
        m.thread_key,
        datetime((m.timestamp_ms)/1000,'unixepoch'), 
        u.contact_id,
        m.sender_id,
        u.name,
        m.text, 
        a.preview_url,
        a.playable_url,
        a.title_text,
        a.subtitle_text,
        a.default_cta_type,
        a.playable_url_mime_type,
        a.filename,
        r.reaction,
        (SELECT name FROM contacts WHERE id = r.actor_id),
        a.playable_duration_ms/1000,
        m.message_id
    FROM messages as m 
    LEFT JOIN attachments AS a ON m.message_id = a.message_id
    JOIN user_contact_info as u ON m.sender_id = u.contact_id
    LEFT JOIN reactions AS r ON m.message_id = r.message_id
    ORDER BY m.timestamp_ms
"""
THREADS_QUERY = """
    SELECT DISTINCT thread_key
    FROM threads
"""


class MessagesCollector():
    def __init__(self):
        pass

def header(html, thread_key, depth):

    ONE_PARTICIPANT_QUERRY = """
        SELECT
            c.profile_picture_url,
            c.name,
            c.profile_picture_large_url, 
            p.thread_key,
            p.contact_id,
            p.nickname
        FROM participants as p 
        JOIN contacts as c ON c.id = p.contact_id
        WHERE p.thread_key = """ + str(thread_key)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(ONE_PARTICIPANT_QUERRY)

    victim_photo = html.header.find(
    "div", attrs={"id": "victimPhoto"})
    victim_name = html.header.find(
    "div", attrs={"id": "victimName"})

    div_row_photo = html.new_tag('div')
    div_row_photo["class"] = "row"
    
    div_row_name = html.new_tag('div')
    div_row_name["class"] = "row"

    suspect_id = utils.get_suspect_id(PATH)

    for row in c:
        pic_url = str(row[0])
        name = str(row[1])
        large_pic_url = str(row[2])
        contact_id = str (row[4])

        if contact_id != suspect_id:
            filetype = utils.get_filetype(pic_url)
            div_col_photo = html.new_tag('div')
            div_col_photo["class"] = "col"
            if (depth == "fast"):
                button_tag = html.new_tag('button')
                button_tag['id'] = str(contact_id) + filetype
                button_tag['class'] = 'btn_download_conversation_contact_image btn btn-outline-dark my-2 my-sm-0 mt-2'
                button_tag['value'] = large_pic_url
                button_tag.append('Download Image')
                div_col_photo.append(button_tag)
            elif (depth == "complete"):
                href_tag = html.new_tag('a')
                href_tag['href'] = f'..\conversations\images\large\{contact_id}' + filetype
                img_tag = html.new_tag('img')
                img_tag['src'] = f'..\conversations\images\small\{contact_id}' + filetype
                img_tag['id'] = 'imgContact'
                href_tag.append(img_tag)
                div_col_photo.append(href_tag)
        
            div_row_photo.append(div_col_photo)
            
            # Fill name
            p_tag = html.new_tag('p')
            p_tag["class"] = "col"
            p_tag.append(name)
            
            div_row_name.append(p_tag)            

    victim_photo.append(div_row_photo)
    victim_name.append(div_row_name)

    return html


def report_html_messages(template_path, depth):

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(MESSAGES_PER_CONVERSATION_QUERRY)
    # Variable initialization
    thread_key = 0
    new_thread_key = 1
    file_write = ""
    last_sender = 0
    last_message_id = 0
    for row in cursor:
        # Query fields
        new_thread_key = row[0]
        datetime = str(row[1])
        sender_id = str(row[3])
        sender_name = str(row[4])
        message = str(row[5])
        attachment_preview_url = str(row[6])
        attachment_playable_url = str(row[7])
        attachment_title = str(row[8])
        attachment_subtitle = str(row[9])
        attachment_type = str(row[10])
        attachment_url_mimetype = str(row[11])
        attachment_filename = str(row[12])
        reaction = str(row[13])
        reaction_sender = str(row[14])
        attachment_duration = str(row[15])
        message_id = str(row[16])

        # BeautifulSoup variables
        html_doc_new_file = ""
        td_message = ""

        has_header = []

        # If is the first conversation file...
        if thread_key == 0:
            thread_key = new_thread_key
            try:
                if not os.path.exists(MESSAGES_PATH):
                    os.makedirs(MESSAGES_PATH)
                new_file_path = MESSAGES_PATH + str(thread_key)+".html"
                # Get template
                template_file = open(template_path, 'r', encoding='utf-8')
                html_doc_new_file = BeautifulSoup(
                    template_file, features='html.parser')
                new_file = open(new_file_path, 'w', encoding='utf-8')
                # Build header
                if thread_key not in has_header:
                    html_doc_new_file = header(html_doc_new_file,thread_key,depth)
                    has_header.append(thread_key)
                # Close file
                template_file.close()
            except IOError as error:
                print(error)
        # If is the same conversation as previous..
        elif thread_key == new_thread_key:
            try:
                previous_file_path = MESSAGES_PATH + str(thread_key) + ".html"
                f = open(previous_file_path, 'r', encoding='utf-8')
                html_doc_new_file = BeautifulSoup(f, features='html.parser')
                new_file = open(previous_file_path, 'w', encoding='utf-8')
                # Close file
                f.close()
            except IOError as error:
                print(error)
        # If is a new conversation..
        elif thread_key != new_thread_key:
            thread_key = new_thread_key
            new_file_path = MESSAGES_PATH + str(thread_key)+".html"
            # Avoid file overwrite, check if file exists
            if Path(new_file_path).is_file():
                try:
                    f = open(new_file_path, 'r', encoding='utf-8')
                    html_doc_new_file = BeautifulSoup(
                        f, features='html.parser')  
                    f.close()
                except IOError as error:
                    print(error)
            else:
                try:
                    # New file, get template_file
                    template_file = open(template_path, 'r', encoding='utf-8')
                    html_doc_new_file = BeautifulSoup(
                        template_file, features='html.parser')
                    # build header
                    if thread_key not in has_header:
                        html_doc_new_file = header(html_doc_new_file,thread_key,depth)
                        has_header.append(thread_key)
                except IOError as error:
                    print(error)
            # Open according file
            new_file = open(new_file_path, 'w', encoding='utf-8')

        # Add <tr> to new file, according to previous thread_key statements(ifs)
        try:
            # TODO (orainha) Verificar se message = null
            # Se for um attachment poderá ser:
            #  - um video: (preview_url + url video + title_text + subtitle_text)
            #  - um attachment: (preview_url + title_text + subtitle_text + default_attachment_title)
            #  - uma imagem (preview_url + title_text + subtitle_text)
            #  - uma chamada perdida (title_text + subtitle_text)
            if not message or message == "" or message == 'None':
                # XXX (orainha) O que é xma_rtc?
                if attachment_type == "xma_rtc_ended_video":
                    td_message = html_doc_new_file.new_tag('td')
                    td_message.append(
                        "Ended " + attachment_title + " - " + attachment_subtitle)
                # XXX (orainha) O que é xma_rtc?
                elif attachment_type == "xma_rtc_missed_video":
                    td_message = html_doc_new_file.new_tag('td')
                    td_message.append(attachment_title +
                                      " at " + attachment_subtitle)
                elif "xma_rtc" in attachment_type:
                    td_message = html_doc_new_file.new_tag('td')
                    td_message.append(attachment_title +
                                      " - " + attachment_subtitle)
                # # Se não tiver "xma_rtc" há de ser outra coisa, e sempre assim
                elif "image" in attachment_url_mimetype:
                    # Get file type
                    filetype = utils.get_filetype(attachment_playable_url)
                    if (depth == "fast"):
                        button_tag = html_doc_new_file.new_tag('button')
                        button_tag['id'] = attachment_filename + filetype
                        button_tag['class'] = 'btn_download_message_image'
                        button_tag['value'] = attachment_playable_url
                        button_tag.append('Download Image')
                        td_message = html_doc_new_file.new_tag('td')
                        td_message.append(button_tag)
                    elif (depth == "complete"):
                        extract_message_file(OUTPUT_PATH, attachment_preview_url, attachment_filename, filetype, str(thread_key))
                        img_tag = html_doc_new_file.new_tag('img')
                        img_tag['src'] = f'..\{MSG_FILES_FOLDER_NAME}\{str(thread_key)}\{attachment_filename}{filetype}'
                        td_message = html_doc_new_file.new_tag('td')
                        td_message.append(img_tag)
                # TODO (orainha) Continuar esta parte, verificar também nos outros casos de threadkey
                elif "audio" in attachment_url_mimetype:
                    # Audio filename already has filetype
                    filetype = ''
                    if (depth == "fast"):
                        button_tag = html_doc_new_file.new_tag('button')
                        button_tag['id'] = attachment_filename
                        button_tag['class'] = 'btn_download_message_file'
                        button_tag['value'] = attachment_playable_url
                        button_tag.append('Download Audio')
                        td_message = html_doc_new_file.new_tag('td')
                        td_message.append(button_tag)
                    elif (depth == "complete"):
                        extract_message_file(OUTPUT_PATH, attachment_playable_url, attachment_filename, filetype, str(thread_key))
                        href_tag = html_doc_new_file.new_tag('a')
                        href_tag['href'] = f'..\{MSG_FILES_FOLDER_NAME}\{str(thread_key)}\{attachment_filename}'
                        href_tag.append(
                            "Audio - " + attachment_title + " - " + attachment_subtitle)
                        td_message = html_doc_new_file.new_tag('td')
                        td_message.append(href_tag)
                elif "video" in attachment_url_mimetype:
                    if (depth == "fast"):
                        button_tag = html_doc_new_file.new_tag('button')
                        button_tag['id'] = attachment_filename
                        button_tag['class'] = 'btn_download_message_file'
                        button_tag['value'] = attachment_playable_url
                        button_tag.append('Download Video')
                        td_message = html_doc_new_file.new_tag('td')
                        td_message.append(button_tag)
                    elif (depth == "complete"):
                        filetype = utils.get_filetype(attachment_preview_url)
                        extract_message_file(OUTPUT_PATH, attachment_preview_url, attachment_filename, filetype, str(thread_key))
                        extract_message_file(OUTPUT_PATH, attachment_playable_url, attachment_filename, '', str(thread_key))
                        img_tag = html_doc_new_file.new_tag('img')
                        # Need to add image filetype on this case, filename ends like '.mp4' (not suitable to show an image)
                        img_tag['src'] = f'..\{MSG_FILES_FOLDER_NAME}\{str(thread_key)}\{attachment_filename}{filetype}'
                        duration = "["+attachment_duration + \
                            "s]" if attachment_duration != "None" else ""
                        title = " - " + attachment_title if attachment_title != "None" else ""
                        subtitle = " - " + attachment_subtitle if attachment_subtitle != "None" else ""
                        img_tag.append("Video " + duration + title + subtitle)
                        href_tag = html_doc_new_file.new_tag('a')
                        # Video filename already has filetype
                        href_tag['href'] = f'..\{MSG_FILES_FOLDER_NAME}\{str(thread_key)}\{attachment_filename}'
                        href_tag.append(img_tag)
                        td_message = html_doc_new_file.new_tag('td')
                        td_message.append(href_tag)
                else:
                    # Can be gifs, files
                    if (depth == "fast"):
                        filetype = ''
                        if (attachment_filename.find('.') > 0):
                            filetype = ''
                        else:
                            filetype = utils.get_filetype(attachment_playable_url)
                            filetype = '.' + filetype
                        button_tag = html_doc_new_file.new_tag('button')
                        button_tag['id'] = attachment_filename + filetype
                        button_tag['class'] = 'btn_download_message_file'
                        if (attachment_preview_url != 'None'):
                            button_tag['value'] = attachment_preview_url
                        elif (attachment_playable_url != 'None'):
                            button_tag['value'] = attachment_playable_url
                        button_tag.append('Download File')
                        td_message = html_doc_new_file.new_tag('td')
                        td_message.append(button_tag)
                    elif (depth == "complete"):
                        filetype = ''
                        # if filename has his filetype written...
                        if (attachment_filename.find('.') > 0):
                            filetype = ''
                        else:
                            filetype = utils.get_filetype(attachment_playable_url)

                        if (attachment_preview_url != 'None'):
                            extract_message_file(OUTPUT_PATH, attachment_preview_url, attachment_filename, filetype, str(thread_key))
                            img_tag = html_doc_new_file.new_tag('img')
                            img_tag['src'] = f'..\{MSG_FILES_FOLDER_NAME}\{str(thread_key)}\{attachment_filename}{filetype}'
                            td_message = html_doc_new_file.new_tag('td')
                            td_message.append(img_tag)

                        elif (attachment_playable_url != 'None'):
                            extract_message_file(OUTPUT_PATH, attachment_playable_url, attachment_filename, filetype, str(thread_key))
                            p_tag = html_doc_new_file.new_tag('p')
                            p_tag.append(attachment_filename)
                            href_tag = html_doc_new_file.new_tag('a')
                            href_tag['href'] = f'..\{MSG_FILES_FOLDER_NAME}\{str(thread_key)}\{attachment_filename}' + '.' + filetype
                            href_tag.append(p_tag)
                            td_message = html_doc_new_file.new_tag('td')
                            td_message.append(href_tag)

            elif "xma_web_url" in attachment_type:
                if (depth == "fast"):
                    filetype = ''
                    # if filename has his filetype written...
                    if (attachment_filename.find('.') > 0):
                        filetype = ''
                    else:
                        filetype = utils.get_filetype(attachment_playable_url)
                    button_tag = html_doc_new_file.new_tag('button')
                    button_tag['id'] = attachment_filename + filetype
                    button_tag['class'] = 'btn_download_message_file'
                    button_tag['value'] = attachment_preview_url
                    button_tag.append('Download Image')
                    td_message = html_doc_new_file.new_tag('td')
                    td_message.append(button_tag)
                    td_message.append(message + " - " + attachment_title + " - " + attachment_subtitle)
                elif (depth == "complete"):
                    filetype = utils.get_filetype(attachment_playable_url)
                    extract_message_file(OUTPUT_PATH, attachment_preview_url, attachment_filename, filetype, str(thread_key))
                    img_tag = html_doc_new_file.new_tag('img')
                    img_tag['src'] = f'..\{MSG_FILES_FOLDER_NAME}\{str(thread_key)}\{attachment_filename}{filetype}'
                    td_message = html_doc_new_file.new_tag('td')
                    td_message.append(img_tag)
                    td_message.append(message + " - " + attachment_title + " - " + attachment_subtitle)
            else:
                td_message = html_doc_new_file.new_tag('td')
                td_message.append(message)


            #New style

            suspect_contact_id = utils.get_suspect_id(PATH)

            # suspect align-right    
            suspect_element_style = "col text-right"
            suspect_element_style_color = "col text-right bg-dark text-white"
            # suspect_element_style_border = "border-radius: 50px 50px 0px 50px;"

            # victim align-left
            victim_element_style = "col text-left"
            victim_element_style_color = "col text-left bg-secondary text-white"
            # victim_element_style_border = "border-radius: 50px 50px 50px 0px;"

            div_row_sender = html_doc_new_file.new_tag('div')
            div_row_sender["class"] = "row"
            small_sender = html_doc_new_file.new_tag('small')
            if(suspect_contact_id == sender_id):
                small_sender["class"] = suspect_element_style
            else:
                small_sender["class"] = victim_element_style
            small_sender.append(sender_name)
            div_empty = html_doc_new_file.new_tag('div')
            div_empty["class"] = "col"
            if(suspect_contact_id == sender_id):
                div_row_sender.append(div_empty)
                div_row_sender.append(small_sender)
            else:
                div_row_sender.append(small_sender)
                div_row_sender.append(div_empty)

            div_row_message = html_doc_new_file.new_tag('div')
            div_row_message["class"] = "row"
            div_message = html_doc_new_file.new_tag('div')
            div_message_content = html_doc_new_file.new_tag('div')
            message = html_doc_new_file.new_tag('td')
            # Must copy td_message to can use on both div and table
            message = copy.copy(td_message)
            if(suspect_contact_id == sender_id):
                div_message_content["id"] = "divMessageContentSuspect"
                div_message_content["class"] = suspect_element_style_color
                # div_message_content["style"] = suspect_element_style_border
            else:
                div_message_content["id"] = "divMessageContentVictim"
                div_message_content["class"] = victim_element_style_color
                # div_message_content["style"] = victim_element_style_border
            div_message_content.append(message)
            div_message.append(div_message_content)
            div_empty = html_doc_new_file.new_tag('div')
            div_empty["class"] = "col"
            if(suspect_contact_id == sender_id):
                div_row_message.append(div_empty)
                div_row_message.append(div_message)
            else:
                div_row_message.append(div_message)
                div_row_message.append(div_empty)

            div_row_datetime = html_doc_new_file.new_tag('div')
            div_row_datetime["class"] = "row"
            div_datetime = html_doc_new_file.new_tag('div')
            if(suspect_contact_id == sender_id):
                div_datetime["class"] = suspect_element_style
            else:
                div_datetime["class"] = victim_element_style
            small_datetime = html_doc_new_file.new_tag('small')
            cite_datetime = html_doc_new_file.new_tag('cite')
            cite_datetime.append(datetime)
            small_datetime.append(cite_datetime)
            div_datetime.append(small_datetime)
            div_empty = html_doc_new_file.new_tag('div')
            div_empty["class"] = "col"
            if(suspect_contact_id == sender_id):
                div_row_datetime.append(div_empty)
                div_row_datetime.append(div_datetime)
            else:
                div_row_datetime.append(div_datetime)
                div_row_datetime.append(div_empty)

            div_row_reaction = html_doc_new_file.new_tag('div')
            div_row_reaction["class"] = "row"
            div_reaction = html_doc_new_file.new_tag('div')
            if(suspect_contact_id == sender_id):
                div_reaction["class"] = suspect_element_style
            else:
                div_reaction["class"] = victim_element_style
            cite_reaction_sender = html_doc_new_file.new_tag('cite')
            cite_reaction_sender.append(reaction_sender)
            div_reaction.append(reaction + " ")
            div_reaction.append(cite_reaction_sender)
            div_empty = html_doc_new_file.new_tag('div')
            div_empty["class"] = "col"
            if(suspect_contact_id == sender_id):
                div_row_reaction.append(div_empty)
                div_row_reaction.append(div_reaction)
            else:
                div_row_reaction.append(div_reaction)
                div_row_reaction.append(div_empty)

            div_container_fluid = html_doc_new_file.new_tag('div')
            if(suspect_contact_id == sender_id):
                div_container_fluid["class"] = "container-fluid mr-5"
            else:
                div_container_fluid["class"] = "container-fluid ml-5"
            div_container_fluid_row = html_doc_new_file.new_tag('div')
            div_container_fluid_row["class"] = "row"
            div_row_w100_suspect = html_doc_new_file.new_tag('div')
            div_row_w100_suspect["class"] = "row w-100"
            div_suspect = html_doc_new_file.new_tag('div')
            div_suspect["id"] = "divSuspect"
            div_suspect["class"] = "col mt-3"
            div_row_w100_victim = html_doc_new_file.new_tag('div')
            div_row_w100_victim["class"] = "row w-100"
            div_victim = html_doc_new_file.new_tag('div')
            div_victim["id"] = "divVictim"
            div_victim["class"] = "col mt-3"
            
            
            if (suspect_contact_id == sender_id):
                #Avoid all message content repeat just because multiple reactions
                if last_message_id != message_id:
                    # Avoid sender name repeat
                    if last_sender != sender_id:
                        div_suspect.append(div_row_sender)
                    div_suspect.append(div_row_message)
                    div_suspect.append(div_row_datetime)
                    if reaction != 'None':
                        div_suspect.append(div_row_reaction)
                        # div_suspect.append(div_row_reaction_sender)
                else:
                    if reaction != 'None':
                        div_suspect.append(div_row_reaction)
                        # div_suspect.append(div_row_reaction_sender)
                div_row_w100_suspect.append(div_suspect)
                div_container_fluid_row.append(div_row_w100_suspect)
                last_sender = sender_id
                last_message_id = message_id
                
            else:
                #Avoid all message content repeat just because multiple reactions
                if last_message_id != message_id:
                    # Avoid sender name repeat
                    if last_sender != sender_id:
                        div_victim.append(div_row_sender)
                    div_victim.append(div_row_message)
                    div_victim.append(div_row_datetime)
                    if reaction != 'None':
                        div_victim.append(div_row_reaction)
                        # div_victim.append(div_row_reaction_sender)
                else:
                    if reaction != 'None':
                        div_victim.append(div_row_reaction)
                        # div_victim.append(div_row_reaction_sender)
                div_row_w100_victim.append(div_victim)
                div_container_fluid_row.append(div_row_w100_victim)
                last_sender = sender_id
                last_message_id = message_id

            div_container_fluid.append(div_container_fluid_row)
            
            html_doc_new_file.table.insert_before(div_container_fluid)

            #Old Style

            tr_tag = html_doc_new_file.new_tag('tr')
            td_datetime = html_doc_new_file.new_tag('td')
            td_datetime.append(datetime)
            td_sender = html_doc_new_file.new_tag('td')
            td_sender.append(sender_name)
            td_reaction = html_doc_new_file.new_tag('td')
            td_reaction.append(reaction)
            td_reaction_sender = html_doc_new_file.new_tag('td')
            td_reaction_sender.append(reaction_sender)
            tr_tag.append(td_datetime)
            tr_tag.append(td_sender)
            tr_tag.append(td_message)
            tr_tag.append(td_reaction)
            tr_tag.append(td_reaction_sender)
            html_doc_new_file.table.tbody.append(tr_tag)

            new_file.seek(0)
            new_file.write(html_doc_new_file.prettify())
            new_file.truncate()

            # has_header = html_doc_new_file.find_all(
            #     "p", attrs={"id": "filename"})
            # if (not has_header):
            #     fill_header(DB_PATH, new_file_path)

            # Close file
            new_file.close()
        except IOError as error:
            print(error)


def report_html_conversations(template_path, depth):
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(CONVERSATIONS_QUERRY)

    # Get template
    template_file = open(template_path, 'r', encoding='utf-8')
    html_doc_new_file = BeautifulSoup(template_file, features='html.parser')
    new_file = open(NEW_FILE_PATH + "conversations.html",
                    'w', encoding='utf-8')

    # Variable initialization
    thread_key = 0
    new_thread_key = 1
    suspect_contact_id = utils.get_suspect_id(PATH)
    for row in c:
        # Query fields
        participant_pic = str(row[0])
        participant_name = str(row[1])
        participant_large_pic = str(row[2])
        new_thread_key = row[3]
        participant_contact_id = row[4]
        # If is the first conversation file...
        if thread_key == 0:
            thread_key = new_thread_key
            tr_tag = html_doc_new_file.new_tag('tr')
            td_conversation = html_doc_new_file.new_tag('td')
            p_tag = html_doc_new_file.new_tag('p')
            p_tag["class"] = "mt-4"
            strong_tag = html_doc_new_file.new_tag('strong')
            strong_tag.append(f"Conversation {str(thread_key)}")
            p_tag.append(strong_tag)
            td_conversation.append(p_tag)
            tr_tag.append(td_conversation)
            html_doc_new_file.table.append(tr_tag)

        # If is the same conversation as previous..
        elif thread_key == new_thread_key:
            if (str(participant_contact_id) != str(suspect_contact_id)):
                pass
            else:
                continue

        # If is a new conversation..
        elif thread_key != new_thread_key:
            if (str(participant_contact_id) != str(suspect_contact_id)):
                thread_key = new_thread_key
                tr_tag = html_doc_new_file.new_tag('tr')
                td_conversation = html_doc_new_file.new_tag('td')
                p_tag = html_doc_new_file.new_tag('p')
                p_tag["class"] = "mt-5"
                strong_tag = html_doc_new_file.new_tag('strong')
                strong_tag.append(f"Conversation {str(thread_key)}")
                p_tag.append(strong_tag)
                td_conversation.append(p_tag)
                tr_tag.append(td_conversation)
                html_doc_new_file.table.append(tr_tag)
            else:
                continue

        tr_tag_data = html_doc_new_file.new_tag('tr')
        tr_tag_data["class"] = "row"
        # td 1
        filetype = utils.get_filetype(participant_pic)
        td_photo = html_doc_new_file.new_tag('td')
        td_photo["class"] = "col-md-2 text-right pr-1"
        if (depth == "fast"):
            button_tag = html_doc_new_file.new_tag('button')
            button_tag['id'] = str(participant_contact_id) + filetype
            button_tag['class'] = 'btn_download_conversation_contact_image btn btn-outline-dark my-2 my-sm-0'
            button_tag['value'] = participant_large_pic
            button_tag.append('Download Image')
            td_photo.append(button_tag)
        elif (depth == "complete"):
            extract_images(NEW_FILE_PATH, participant_pic, participant_large_pic, filetype, str(participant_contact_id))
            href_tag = html_doc_new_file.new_tag('a')
            href_tag['href'] = f'conversations\images\large\{participant_contact_id}' + filetype
            img_tag = html_doc_new_file.new_tag('img')
            img_tag['src'] = f'conversations\images\small\{participant_contact_id}' + filetype
            img_tag['id'] = 'imgContact'
            href_tag.append(img_tag)
            td_photo.append(href_tag)
        # td 2
        td_msgs = html_doc_new_file.new_tag('td')
        td_msgs["class"] = "col-md-10"
        td_msgs["id"] = "tdContactName"
        href_msgs_tag = html_doc_new_file.new_tag('a')
        href_msgs_tag["href"] = f'messages\{str(thread_key)}.html'
        href_msgs_tag["target"] = 'targetframemessages'
        href_msgs_tag.append(str(participant_name))
        td_msgs.append(href_msgs_tag)
        tr_tag_data.append(td_photo)
        tr_tag_data.append(td_msgs)
        html_doc_new_file.table.append(tr_tag_data)
    new_file.seek(0)
    new_file.write(html_doc_new_file.prettify())
    new_file.truncate()


def report_csv_conversations(delim):
    # XXX (ricardoapl) Remove reference to DB_PATH?
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute(CONVERSATIONS_QUERRY)
        rows = cursor.fetchall()
        cursor.close()
    # XXX (ricardoapl) Columns is highly dependant on the query,
    #     if we change query we also have to change columns.
    columns = [
        'profile_picture_url',
        'name',
        'profile_picture_large_url',
        'thread_key',
        'contact_id',
        'nickname'
    ]
    # XXX (ricardoapl) Remove reference to NEW_FILE_PATH?
    filename = NEW_FILE_PATH + 'conversations.csv'
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=delim, quotechar='|',
                            quoting=csv.QUOTE_MINIMAL)
        writer.writerow(columns)
        writer.writerows(rows)


def report_csv_messages(delim):
    # XXX (ricardoapl) Remove reference to DB_PATH?
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute(THREADS_QUERY)
        thread_rows = cursor.fetchall()
        cursor.execute(MESSAGES_PER_CONVERSATION_QUERRY)
        msg_rows = cursor.fetchall()
        cursor.close()
    # XXX (ricardoapl) Careful! Columns is highly dependant on the query,
    #     if we change query we also have to change columns.
    columns = [
        'thread_key',
        'datetime',
        'contact_id',
        'sender_id',
        'name',
        'text',
        'preview_url',
        'playable_url',
        'title_text',
        'subtitle_text',
        'default_cta_type',
        'playable_url_mime_type',
        'filename',
        'reaction',
        'actor_name',
        'playable_duration_ms'
    ]
    thread_idx = columns.index('thread_key')
    threads = [row[thread_idx] for row in thread_rows]
    for thread in threads:
        thread_messages = filter(lambda row: (
            row[thread_idx] == thread), msg_rows)
        # XXX (ricardoapl) Remove reference to MESSAGES_PATH?
        filename = MESSAGES_PATH + str(thread) + '.csv'
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=delim, quotechar='|',
                                quoting=csv.QUOTE_MINIMAL)
            writer.writerow(columns)
            writer.writerows(thread_messages)


def report_csv(delim):
    report_csv_conversations(delim)
    report_csv_messages(delim)


def input_file_path(user_path):
    # XXX (orainha) Procurar por utilizadores dando apenas o drive?
    global DB_PATH
    global PATH
    PATH = utils.get_input_file_path(user_path)
    DB_PATH = utils.get_db_path(PATH)

def output_file_path(destination_path):
    global NEW_FILE_PATH
    global MESSAGES_PATH
    NEW_FILE_PATH = utils.get_output_file_path(destination_path)
    MESSAGES_PATH = NEW_FILE_PATH + "messages\\"
    try:
        if os.path.exists(MESSAGES_PATH):
            shutil.rmtree(MESSAGES_PATH)
        if not os.path.exists(MESSAGES_PATH):
            os.makedirs(MESSAGES_PATH)
    except IOError as error:
        print(error)
        sys.exit()


def extract_message_file(path, url, filename, filetype, msg_thread_key):
    global OUTPUT_PATH
    global MSG_FILES_FOLDER_NAME
    OUTPUT_PATH = os.path.expandvars(path)
    MSG_FILES_FOLDER_NAME = 'message-files'
    IMAGES_PATH = OUTPUT_PATH + f'\\{MSG_FILES_FOLDER_NAME}\{msg_thread_key}'
    utils.extract(path, IMAGES_PATH, url, filename, filetype)


def extract_images(output_path, small_pic_url, large_pic_url, filetype, filename):
    global OUTPUT_PATH
    FILENAME = 'conversations.html'
    OUTPUT_PATH = os.path.expandvars(output_path)
    SMALL_IMAGES_PATH = OUTPUT_PATH + f'\conversations\images\small'
    LARGE_IMAGES_PATH = OUTPUT_PATH + f'\conversations\images\large'
    FILENAME = OUTPUT_PATH + f'\\{FILENAME}'

    utils.extract(output_path, SMALL_IMAGES_PATH, small_pic_url, filename, filetype)
    utils.extract(output_path, LARGE_IMAGES_PATH, large_pic_url, filename, filetype)