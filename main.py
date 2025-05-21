import os
import shutil

if __name__ == '__main__':
    # 读取 mineru 文件下的所有文件夹
    folders = os.listdir(os.path.join(os.getcwd(),'mineru'))
    
    # create a container to store all the data
    files = []
    
    # 遍历所有文件夹
    for folder in folders:
        # 读取文件夹下的 md 文件
        folder_files = os.listdir(os.path.join(os.getcwd(),'mineru', folder))
        for file in folder_files:
            if file.endswith('.md'):
                files.append(os.path.join(os.getcwd(),'mineru', folder, file))
    
    # 遍历所有 md 文件
    for file in files:
        # 将文件 copy 到 md 文件夹下
        shutil.copy(file, os.path.join(os.getcwd(),'md'))
     
        
     