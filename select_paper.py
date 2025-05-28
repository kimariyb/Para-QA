import os
import pathlib
import shutil
import pandas as pd

from tqdm import tqdm


if __name__ == '__main__':
    # read the csv file
    df = pd.read_csv('./selected_paper_names.csv', header=None)
    
    # format the data
    df.columns = ['paper_name']
    
    # get the list of paper names
    paper_names = df['paper_name'].tolist()
    
    # delete the 1. 2. ...
    # and delete the 
    paper_names = [
        os.path.splitext(name.split('. ')[-1])[0]
        for name in paper_names
    ]
          

    # get the file list
    file_list = os.listdir('./cleaned')
    
    for file in tqdm(file_list):
        file_name = pathlib.Path(file).stem
        
        if file_name in paper_names:
            # copy the file to selected folder
            print(f'Copying {file}')
            
            # copy the file
            shutil.copy(
                src=pathlib.Path(f'./cleaned/{file}'),
                dst=pathlib.Path(f'./selected/{file}')
            )
    