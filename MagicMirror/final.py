import cv2
import mediapipe as mp
import numpy as np
import math
from rembg import remove
from PIL import Image

# 이미지 로드
#input_image = Image.open('/home/mirror/photo.jpg')
input_image = Image.open('human.jpg')

# 배경 제거
output_image = remove(input_image)

# 이미지 저장
output_image.save('human.png')

print(np.__version__)
#신체 요소 길이 측정
factor = np.zeros(11) 

#체형 분류 0:큰삼각체 1:역삼각체 2:사각체
category = np.zeros(3)

# Mediapipe 솔루션 초기화
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_pose = mp.solutions.pose

# 이미지 파일 경로
IMAGE_FILE = 'human.png'

# Mediapipe Pose 설정
with mp_pose.Pose(
        static_image_mode=True,
        model_complexity=2,
        enable_segmentation=True,
        min_detection_confidence=0.5) as pose:
    
    # 이미지 읽기
    image = cv2.imread(IMAGE_FILE)
    
    # 이미지가 제대로 불러와졌는지 확인
    if image is None:
        print(f"이미지 파일을 불러오는데 실패했습니다: {IMAGE_FILE}")
    else:
        image_height, image_width, _ = image.shape
        
        # 처리 전 BGR 이미지를 RGB로 변환합니다.
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)
        
        coords_list = []
        # 포즈 랜드마크가 감지되었는지 확인합니다.
        if results.pose_landmarks:
            # 각 특징점의 좌표를 출력합니다.
            for idx, landmark in enumerate(results.pose_landmarks.landmark):
                x = landmark.x * image_width
                y = landmark.y * image_height
                coords = (x, y)
                coords_list.append(coords)
                
                #print(f"Landmark {idx}: (x: {x}, y: {y})")
            location = np.array(coords_list)
            
            # 이미지 위에 포즈 랜드마크를 그립니다.
            annotated_image = image.copy()
            mp_drawing.draw_landmarks(
                annotated_image,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style())
            
            # 세그멘테이션 마스크 얻기
            mask = results.segmentation_mask
            mask = np.where(mask > 0.1, 1, 0).astype(np.uint8)  # Thresholding for better segmentation
            person_segment = cv2.bitwise_and(image, image, mask=mask)
        
            #좌표 신체 요소로 추출
            factor[1] = round(location[29][1] - location[11][1]) #어깨높이
            
            under_x = round(location[15][0] - location[13][0])**2
            under_y = round(abs(location[13][1] - location[15][1]))**2
            factor[3] = round(math.sqrt(under_x + under_y)) #아래팔길이
            
            shoulder_x = round(location[11][0] - location[12][0])**2
            shoulder_y = round(abs(location[11][1] - location[12][1]))**2

            factor[5] = round(math.sqrt(shoulder_x + shoulder_y)) #어깨 너비
            
            up_x = round(location[13][0] - location[11][0])**2
            up_y = round(abs(location[11][1] - location[13][1]))**2
            factor[6] = round(math.sqrt(up_x + up_y)) #위팔길이

            #총길이
            #사진 흑백으로 전환
            gray = cv2.cvtColor(person_segment, cv2.COLOR_BGR2GRAY)
            # 이진화 (Thresholding)
            _, threshold = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            # 윤곽선 찾기
            contours, _ = cv2.findContours(threshold, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            # 윤곽선 중 가장 높은 y좌표 찾기
            highest_point = None
            for contour in contours:
                for point in contour:
                    if (highest_point is None or point[0][1] < highest_point[1]) and point[0][1] != 0:
                        highest_point = tuple(point[0])
            
            # Haar Cascade 얼굴 검출기 초기화
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            # 흑백 이미지로 변환 (얼굴 검출기는 흑백 이미지를 요구합니다)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # 얼굴 검출
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            for (x, y, w, h) in faces:
                cv2.rectangle(image, (x, y), (x+w, y+h), (255, 0, 0), 2)
                # 턱 좌표 계산 (간단히 얼굴 영역의 가장 아래 점으로 가정)
                jaw_x = x + w // 2
                jaw_y = y + h
                factor[8] = round(jaw_y - highest_point[1])
                #몸통 수직길이
                factor[10] = round(location[22][1] - jaw_y)
                # 턱 좌표에 빨간색 점 그리기
                cv2.circle(image, (jaw_x, jaw_y), 5, (0, 0, 255), -1)

            #총길이
            factor[7] = round(location[29][1] - highest_point[1])
            
            #비율 
            # height = float(input("키를 입력하세요: "))
            try:
                with open('/home/mirror/height.txt', 'r') as f:
                   height = float(f.read().strip())
            except FileNotFoundError:
                raise ValueError("Height file not found. Please enter your height using the MagicMirror module.")
            rat = height / factor[7]

            #샅높이
            factor[9] = round(location[29][1] - location[22][1])
            #머리길이
            #factor[8] = round(jaw_y - highest_point[1])

            print("키: ", round(factor[7] * rat, 1))
            print("어깨높이: ", round(factor[1] * rat, 1))
            print("아래팔길이: ", round(factor[3] * rat, 1))
            print("어깨너비: ", round(factor[5] * rat, 1))
            print("위팔길이: ", round(factor[6] * rat, 1))
            print("머리 길이: ", round(factor[8] * rat, 1))
            print("샅높이: ", round(factor[9] * rat, 1))
            print("몸통수직길이: ", round(factor[10] * rat, 1))

            shouldery = round(factor[1] * rat, 1)
            head = round(factor[8] * rat, 1)
            under_arm = round(factor[3] * rat, 1)
            minus = round(factor[9] * rat, 1) - round(factor[10] * rat, 1)
            shoulderx = round(factor[5] * rat, 1)
            up_arm = round(factor[6] * rat, 1)

            # 체형 분류
            if shouldery < 129.4:
                category[0] += 1
            elif 129.4 <= shouldery <= 130.4:
                category[1] += 1
            elif 130.4 <  shouldery * rat:
                category[2] += 1


            # 머리크기 분류
            if 22.3 <=  head:
                category[0] += 1
            elif  head <= 22.3:
                category[1] += 1
                category[2] += 1
  
            # 아래팔길이 분류
            if 24.8 <=  under_arm:
                category[0] += 1
            elif under_arm <= 24.4:
                category[1] += 1
            elif 24.5 <=  under_arm <= 24.7:
                category[2] += 1

            # 샅높이-몸통수직길이 분류
            if 8.2 <= minus:
                category[0] += 1
            elif 7.9 <= minus < 8.2:
                category[1] += 1
            elif minus < 7.9:
                category[2] += 1

            # 어깨너비 분류
            if  35.8 <= shoulderx < 36.8:
                category[0] += 1
            elif 36.8 <= shoulderx:
                category[1] += 1
            elif shoulderx < 35.8:
                category[2] += 1


            # 위팔길이 분류
            if 31.0 <= up_arm:
                category[0] += 1
            elif 30.5 <= up_arm <= 31.0:
                category[1] += 1
                category[2] += 1

            #결과출력
            max_index = np.argmax(category)
            if max_index == 0:
                print("큰삼각체형")
                bodytype = "largeTri"
            elif max_index == 1:
                print("역삼각체형")
                bodytype = "inverTri"
            else:
                print("사각체형")
                bodytype = "square"


            with open('/home/mirror/information.txt', 'w') as f:
                f.write(f"키: {round(factor[7] * rat, 1)}\n")
                f.write(f"어깨높이: {round(factor[1] * rat, 1)}\n")
                f.write(f"아래팔길이: {round(factor[3] * rat, 1)}\n")
                f.write(f"어깨너비: {round(factor[5] * rat, 1)}\n")
                f.write(f"위팔길이: {round(factor[6] * rat, 1)}\n")
                f.write(f"머리 길이: {round(factor[8] * rat, 1)}\n")
                f.write(f"샅높이: {round(factor[9] * rat, 1)}\n")
                f.write(f"몸통수직길이: {round(factor[10] * rat, 1)}\n")

            with open('/home/mirror/result.txt', 'w') as f:
                f.write(f"{bodytype}\n")




            # print(category[0])
            # print(category[1])
            # print(category[2])

            # 결과 이미지를 화면에 표시합니다.
            cv2.imshow('Annotated Image', annotated_image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            
            # 결과를 이미지에 그리기
            if highest_point:
                cv2.circle(image, highest_point, 5, (0, 255, 0), -1)
            cv2.imshow("Image with Highest Point", image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
