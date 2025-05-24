import os
import shutil

from tqdm import tqdm
from utils.parser import MarkdownProcessor


def transfer_mineru_files(src_dir, dst_dir):
    # 读取 mineru 文件下的所有文件夹
    folders = os.listdir(os.path.join(os.getcwd(), src_dir))
    
    # create a container to store all the data
    files = []
    
    # 遍历所有文件夹
    for folder in tqdm(folders, desc='Scanning Mineru files'):
        # 读取文件夹下的 md 文件
        folder_files = os.listdir(os.path.join(os.getcwd(), src_dir, folder))
        for file in folder_files:
            if file.endswith('.md'):
                files.append(os.path.join(os.getcwd(), src_dir, folder, file))
    
    for file in tqdm(files, desc='Copying Mineru files'):
        # 将文件 copy 到 md 文件夹下
        shutil.copy(file, os.path.join(os.getcwd(), dst_dir))


if __name__ == '__main__':
    # transfer_mineru_files('mineru', 'md')
   
    processor = MarkdownProcessor('md', 'output')
    processor.process_md('./md/10.1002_advs.202207112.md', 'output')
    print('Done')
     
        
     