from utils.dify import FileUploadClient, WorkFlowRunClient
from tqdm import tqdm

import os

TAG_API_KEY = "app-E5sGhvlfMQKOeSJBh86lSbDM"
CLEAN_API_KEY = "app-yu6OCcvu2XzHHR7ruJjcdqiY"
UPLOAD_FILE_URL = "http://localhost/v1/files/upload"
WORKFLOW_RUN_URL = "http://localhost/v1/workflows/run"
USER = "abc-123"


def batch_execute_workflow(target_folder, api_key=None):
    file_upload_client = FileUploadClient(api_key=api_key, base_url=UPLOAD_FILE_URL, user=USER)
    workflow_run_client = WorkFlowRunClient(api_key=api_key, base_url=WORKFLOW_RUN_URL, user=USER)
    
    for file_path in tqdm(os.listdir(target_folder)):
        file_path = os.path.join(target_folder, file_path)
        
        # upload the file to the server
        file_upload_response = file_upload_client.request(file_path)
        # get the file upload id
        file_upload_id = file_upload_response.get("id")
        # run the workflow with the file upload id as input parameter
        workflow_run_response = workflow_run_client.request(param_name="input_file", upload_file_id=file_upload_id)

    return workflow_run_response


if __name__ == "__main__":
    tags_target_folder = "D:\\project\\SABRE-RAG\\cleaned"
    
    # # tagging the files
    # batch_execute_workflow(tags_target_folder, api_key=TAG_API_KEY)
    
    # clean the files
    selected_target_folder = "D:\\project\\SABRE-RAG\\selected"
    
    batch_execute_workflow(selected_target_folder, api_key=CLEAN_API_KEY)
    