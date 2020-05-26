import cv2
import numpy as np
import datetime
import ibm_boto3
from ibm_botocore.client import Config, ClientError
import time
#CloudantDB
from cloudant.client import Cloudant
from cloudant.error import CloudantException
from cloudant.result import Result, ResultByKey
import requests

from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from playsound import playsound

import json
from watson_developer_cloud import VisualRecognitionV3

# Constants for IBM COS values
COS_ENDPOINT = "https://s3.jp-tok.cloud-object-storage.appdomain.cloud" # Current list avaiable at https://control.cloud-object-storage.cloud.ibm.com/v2/endpoints
COS_API_KEY_ID = "veZRw9HMG_joB_PNWfbkwo57R9jI0p5kvY8wrst_HAFl" # eg "W00YiRnLW4a3fTjMB-odB-2ySfTrFBIQQWanc--P3byk"
COS_AUTH_ENDPOINT = "https://iam.cloud.ibm.com/identity/token"
COS_RESOURCE_CRN = "crn:v1:bluemix:public:cloud-object-storage:global:a/40c46a853021447092943d3bf060fe66:0cf56133-1937-4855-af03-2f9be53189ab::" # eg "crn:v1:bluemix:public:cloud-object-storage:global:a/3bf0d9003abfb5d29761c3e97696b71c:d6f04d83-6c4f-4a62-a165-696756d63903::"

# Create resource
cos = ibm_boto3.resource("s3",
    ibm_api_key_id=COS_API_KEY_ID,
    ibm_service_instance_id=COS_RESOURCE_CRN,
    ibm_auth_endpoint=COS_AUTH_ENDPOINT,
    config=Config(signature_version="oauth"),
    endpoint_url=COS_ENDPOINT
)

def create_bucket(bucket_name):
    print("Creating new bucket: {0}".format(bucket_name))
    try:
        cos.Bucket(bucket_name).create(
            CreateBucketConfiguration={
                "LocationConstraint":"jp-tok-standard"
            }
        )
        print("Bucket: {0} created!".format(bucket_name))
    except ClientError as be:
        print("CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to create bucket: {0}".format(e))

create_bucket("kareti")

visual_recognition = VisualRecognitionV3(
    '2018-03-19',
    iam_apikey='uOIt_ok57VcZn6xCcZMyEPNHL-VeX96nRnlj4azpxp_4')

#Provide CloudantDB credentials such as username,password and url
client = Cloudant("45793cc6-68c2-457d-9936-9acd2774d2f0-bluemix", "85d9ae991b298f8f60a5857b8b4201573d2b9ca988c5a2abbf073643ac0562b7", url="https://45793cc6-68c2-457d-9936-9acd2774d2f0-bluemix:85d9ae991b298f8f60a5857b8b4201573d2b9ca988c5a2abbf073643ac0562b7@45793cc6-68c2-457d-9936-9acd2774d2f0-bluemix.cloudantnosqldb.appdomain.cloud")
client.connect()

#Provide your database name
database_name = "bhavana"
my_database = client.create_database(database_name)

if my_database.exists():
   print(f"'{database_name}' successfully created.")

#It will read the first frame/image of the video
video=cv2.VideoCapture(0)
while True:
    #capture the first frame
    check,frame=video.read()
    gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    time.sleep(5)
    picname=datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
    cv2.imwrite(picname+".jpg",frame)
    
    #waitKey(1)- for every 1 millisecond new frame will be captured
    Key=cv2.waitKey(1)
    if Key==ord('q'):
        #release the camera
        video.release()
        #destroy all windows
        cv2.destroyAllWindows()
        break
    with open('./'+picname+'.jpg', 'rb') as images_file:
        classes = visual_recognition.classify(
            images_file,
            threshold='0.6',
            classifier_ids='Team09_657499471').get_result()
	
    a=json.dumps(classes, indent=2)
    b=json.loads(a)
    print(b)
    c=b['images']

    for i in c:
        for j in i['classifiers']:
            k=j['classes']
            for l in k:
               print(l['class'])
    x=l['class']

    def multi_part_upload(bucket_name, item_name, file_path):
        try:
            print("Starting file transfer for {0} to bucket: {1}\n".format(item_name, bucket_name))

            # set 5 MB chunks
            part_size = 1024 * 1024 * 5

            # set threadhold to 15 MB
            file_threshold = 1024 * 1024 * 15

            # set the transfer threshold and chunk size
            transfer_config = ibm_boto3.s3.transfer.TransferConfig(
                multipart_threshold=file_threshold,
                multipart_chunksize=part_size
            )

            # the upload_fileobj method will automatically execute a multi-part upload
            # in 5 MB chunks for all files over 15 MB
            with open(file_path, "rb") as file_data:
                cos.Object(bucket_name, item_name).upload_fileobj(
                    Fileobj=file_data,
                    Config=transfer_config
                )

            print("Transfer for {0} Complete!\n".format(item_name))
        except ClientError as be:
            print("CLIENT ERROR: {0}\n".format(be))
        except Exception as e:
            print("Unable to complete multi-part upload: {0}".format(e))
    multi_part_upload("kareti", picname+".jpg", picname+".jpg")
    json_document={"link":COS_ENDPOINT+"/"+"kareti"+"/"+picname+".jpg"}
    new_document = my_database.create_document(json_document)

    authenticator = IAMAuthenticator('qiXzgBiIKN32QXgXegbxJ3-OzPMh4eDeEeuEQyaO0eUj')
    text_to_speech = TextToSpeechV1(
        authenticator=authenticator
    )

    text_to_speech.set_service_url('https://api.au-syd.text-to-speech.watson.cloud.ibm.com/instances/4b76ef9d-bc67-4762-9fca-7169c9140d05')

    with open('kareti1.mp3', 'wb') as audio_file:
        if(x=="Humans"):
                audio_file.write(
                        text_to_speech.synthesize(
                                f' the object is {x}',
                                voice='en-US_AllisonVoice',
                                accept='audio/mp3'
                                ).get_result().content)

        else:
                audio_file.write(
                        text_to_speech.synthesize(
                                f' the object is {x}',
                                voice='en-US_AllisonVoice',
                                accept='audio/mp3'
                                ).get_result().content)




                import requests
                r = requests.get('https://www.fast2sms.com/dev/bulk?authorization=F5VGTe8iUzn6S2PfRLXD0B9gY4haowsEcyK7MZmxqpk3luCdAOVbwHK27aNkrS5cIqOztxlT9MsdvCfR&sender_id=FSTSMS&message=Animal is detected in cameras&language=english&route=p&numbers=9182382058')
                print(r.status_code)


        
    playsound('kareti1.mp3')

        

