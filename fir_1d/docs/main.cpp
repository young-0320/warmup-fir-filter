#include<iostream>
#include<fstream>
#include"complex.h"
using namespace std;

#define BYTE unsigned char // 0~255 까지의 unsigned char 자료형을 앞으로 BYTE 라는 단어로 사용 
#define PI 3.141592
#define INPUT_FILE_NAME1 "Lena_gray.bmp"
#define INPUT_FILE_NAME2 "Lena_gray_NOISE.bmp"
#define HEADERSIZE 1078 // Lena_gray.bmp 파일의 헤더의 크기

void main()
{
	// 이미지 저장 코드

	ifstream In_Image; // 파일 읽기
	In_Image.open(INPUT_FILE_NAME1, ios::in | ios::binary); // INPUT_FILE_NAME1 파일을 binary로 읽어옴

	int M = 64, N = 64; // 이미지의 크기 정의(단위:픽셀) 
	BYTE* header = new BYTE[HEADERSIZE]; // 이미지의 헤더 정보를 담기 위한 공간 생성
	BYTE** image = new BYTE*[N]; // Lena_gray.bmp 파일의 이미지 데이터를 담기 위한 공간 생성
	BYTE** r = new BYTE*[N]; // 이미지 데이터 중 red에 대한 데이터를 담을 공간 생성
	BYTE** g = new BYTE*[N]; // 이미지 데이터 중 green에 대한 데이터를 담을 공간 생성
	BYTE** b = new BYTE*[N]; // 이미지 데이터 중 blue에 대한 데이터를 담을 공간 생성
	BYTE** result = new BYTE*[N]; // DFT와 IDFT를 통해 노이즈를 제거한 이미지 데이터를 담기 위한 공간 생성
	for (int i = 0; i < N; i++) { // 각각의 데이터를 담을 공간을 2차원의 형태로 만드는 과정(왜냐하면 이미지가 2차원이기 때문)
		image[i] = new BYTE[M * 3]; // 이미지 데이터을 담을 공간의 크기 : N * (M*3) (한 픽셀은 R,G,B 성분으로 이루어져 있으므로 행의 크기는 64*3이 되어야 함) 
		r[i] = new BYTE[M]; // red에 대한 데이터를 담을 공간의 크기 : N * M 
		g[i] = new BYTE[M]; // green에 대한 데이터를 담을 공간의 크기 : N * M 
		b[i] = new BYTE[M]; // blue에 대한 데이터를 담을 공간의 크기 : N * M 
		result[i] = new BYTE[M * 3]; // 노이즈를 제거한 이미지 데이터을 담을 공간의 크기 : N * (M*3) (출력 이미지 생성을 위해 한 픽셀에 R,G,B 성분이 모두 들어가야 함) 
	}

	In_Image.read((char*)header, HEADERSIZE); // 헤더 정보를 HEADERSIZE의 크기만큼 읽어서 header 변수에 저장
	for (int i = 0; i < N; i++) {
		In_Image.read((char*)image[i], 3 * M); // Lena_gray.bmp 파일의 이미지 데이터를 읽고 이를 image 변수에 저장 
	}

	int place;
	for (int i = 0; i < N; i++) {
		for (int j = 0; j < M; j++) { // 이미지 데이터가 저장되어 있는 image 변수에서 R,G,B 값을 복사(실제 BMP 파일에는 B,G,R 순으로 담겨 있음)
			place = 3 * j;
			b[i][j] = image[i][place];  // blue 데이터 
			g[i][j] = image[i][place + 1]; // green 데이터
			r[i][j] = image[i][place + 2];  // red 데이터
		}
	}

	/* 작성해야 하는 코드 부분

	// 2D DFT 함수 코드로 구현
	// 2D DFT 이미지 출력 (Hint : DFT값은 매우 크기 때문에 정규화 작업을 실행해야 합니다)
	// 노이즈 제거 
	// 2D IDFT 함수 코드로 구현

	*/

	// 이미지 생성 코드

	for (int i = 0; i < N; i++) {
		for (int j = 0; j < M; j++) { // DFT와 IDFT를 통해 노이즈를 제거한 데이터를 result 변수에 하나로 묶기(BMP 파일 생성을 위해 한 픽셀은 24 bit(R,G,B)로 구성되야 함)
			place = 3 * j;
			result[i][place] = b[i][j];  // gray 이미지는 R,G,B 값이 모두 같으므로 하나의 변수만 이용해서 저장해도 됨
			result[i][place + 1] = g[i][j];
			result[i][place + 2] = r[i][j];
		}
	}

	ofstream Out;
	Out.open("result.bmp", ios::out | ios::binary); // 출력 파일 생성
	Out.write((char*)header, HEADERSIZE); // 출력파일에 이미지의 헤더정보 작성
	for (int i = 0; i < N; i++) {
		Out.write((char*)result[i], 3 * M); // 노이즈를 제거하고 R,G,B이 하나의 픽셀에 묶인 result 데이터를 출력 파일에 작성
	}

	system("pause");
	return;
}