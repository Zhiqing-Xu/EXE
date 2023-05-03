#!/usr/bin/env python
# coding: utf-8
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$#
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$#
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$#
# The following code ensures the code work properly in 
# MS VS, MS VS CODE and jupyter notebook on both Linux and Windows.
#--------------------------------------------------#
import os 
import sys
import os.path
from sys import platform
from pathlib import Path
#--------------------------------------------------#
if __name__ == "__main__":
    print("="*80)
    if os.name == 'nt' or platform == 'win32':
        print("Running on Windows")
        if 'ptvsd' in sys.modules:
            print("Running in Visual Studio")
#--------------------------------------------------#
    if os.name != 'nt' and platform != 'win32':
        print("Not Running on Windows")
#--------------------------------------------------#
    if "__file__" in globals().keys():
        print('CurrentDir: ', os.getcwd())
        try:
            os.chdir(os.path.dirname(__file__))
        except:
            print("Problems with navigating to the file dir.")
        print('CurrentDir: ', os.getcwd())
    else:
        print("Running in python jupyter notebook.")
        try:
            if not 'workbookDir' in globals():
                workbookDir = os.getcwd()
                print('workbookDir: ' + workbookDir)
                os.chdir(workbookDir)
        except:
            print("Problems with navigating to the workbook dir.")
#--------------------------------------------------#

###################################################################################################################
###################################################################################################################
# Imports
import requests 
import threading
#--------------------------------------------------#
# To manage the queue for threading
from queue import Queue
#--------------------------------------------------#
# To obtain user agent for requests
from feapder.network.user_agent import get
#--------------------------------------------------#
# For logging purposes
from loguru import logger
#--------------------------------------------------#
# For retry mechanism in case of failures
from tenacity import retry, stop_after_attempt


###################################################################################################################
###################################################################################################################
class DownloadFile(object):
    
    def __init__(self):

        # The URL to be queried. The '{}' will be filled with specific ID numbers
        self.url = "https://www.brenda-enzymes.org/molfile.php?LigandID={}"

        # Headers for the HTTP request
        self.headers = {
            'Host': 'www.brenda-enzymes.org',
            'Referer': 'https://www.brenda-enzymes.org/ligand.php?brenda_ligand_id=68',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
        }

        # Queue for managing URLs to be processed
        self.url_queue = Queue()

        # Queue for managing file save operations
        self.save_queue = Queue()


    # 'retry' decorator ensures the function to retry up to 5 times in case of failure
    @retry(stop = stop_after_attempt(5))
    def query(self, url): # Function to get content from URL
        
        self.headers['User-Agent'] = get()
        headers = self.headers

        # Send GET request and get response content
        response = requests.get(url, headers=headers, timeout = 30).content

        return response

    def save(self): # Function to save content to local file

        while True:

            # Get next save operation from queue
            save_item = self.save_queue.get()

            # Construct file name
            filename = save_item['id'] + ".mol"

            # Open file and write content
            with open('./Z02_All_Ligands_Molfiles/' + filename, 'wb+') as fp:
                fp.write(save_item['content'])

            # Log successful file save
            logger.success("Successfully Saved File: " + filename)

            # Mark the task as done in the queue
            self.save_queue.task_done()


    def get_url(self): # Function to generate URLs to be queried

        for i in range(269999, 300000):

            # Format URL with ID
            url = self.url.format(i)

            # Create item with ID and URL
            item = {"id": str(i), 'url': url}

            # Put the item in the URL queue
            self.url_queue.put(item)

    def get_content(self): # Function to get content from URLs
        
        while True:

            # Get next URL from queue
            item = self.url_queue.get()
            url = item['url']
            id = item['id']

            # Get content from URL
            content = self.query(url)

            # Create save item with ID and content
            save_item = {'id': id, 'content': content}

            # Put the save item in the save queue
            self.save_queue.put(save_item)

            # Mark the task as done in the queue
            self.url_queue.task_done()

    def run(self): # Function to start the multithreaded downloading and saving process

        # List to hold all threads
        t_list = []  

        # Create and start a thread for URL generation
        t_get_url = threading.Thread(target = self.get_url)
        t_list.append(t_get_url)

        # Create and start 5 threads for content fetching
        for i in range(5):
            t_get_content = threading.Thread(target = self.get_content)
            t_list.append(t_get_content)

        # Create and start 5 threads for saving the content
        for i in range(5):
            t_save = threading.Thread(target = self.save)
            t_list.append(t_save)

        # Start all threads
        for t in t_list:
            t.start()

        # Wait for all tasks in the queue to be done before exiting
        for q in [self.url_queue, self.save_queue]:
            q.join()


if __name__ == '__main__':
    # Instantiate the DownloadFile class and start the download process
    down = DownloadFile()
    down.run()







