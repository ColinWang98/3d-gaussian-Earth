#include <Wire.h>
#include "MAX30105.h"
#include "heartRate.h"

MAX30105 particleSensor;
const byte RATE_SIZE = 4; //Increase this for more averaging. 4 is good.
byte rates[RATE_SIZE]; //Array of heart rates
byte rateSpot = 0;
long lastBeat = 0; //Time at which the last beat occurred
float beatsPerMinute;
int Bpm_value = 0;

void setup(){
  Serial.begin(9600);
  
  // 等待串口连接（可选，用于调试）
  // while (!Serial) {
  //   ; // 等待串口连接，仅在需要调试时取消注释
  // }
  
  particleSensor.begin(Wire, I2C_SPEED_FAST);
  particleSensor.setup(); //Configure sensor with default settings
  particleSensor.setPulseAmplitudeRed(0x0A); //Turn Red LED to low to indicate sensor is running
  particleSensor.setPulseAmplitudeGreen(0); //Turn off Green LED
  
  Serial.println("MAX30105 心率传感器已启动");
}

void loop(){
  long irValue = particleSensor.getIR();
  
  if (checkForBeat(irValue) == true)
  {
    //We sensed a beat!
    long delta = millis() - lastBeat;
    lastBeat = millis();
    beatsPerMinute = 60 / (delta / 1000.0);
    
    if (beatsPerMinute < 255 && beatsPerMinute > 20)
    {
      rates[rateSpot++] = (byte)beatsPerMinute; //Store this reading in the array
      rateSpot %= RATE_SIZE; //Wrap variable
      
      //Take average of readings
      Bpm_value = 0;
      for (byte x = 0 ; x < RATE_SIZE ; x++)
        Bpm_value += rates[x];
      Bpm_value /= RATE_SIZE;
      
      // 输出前端可识别的格式：HR:75
      // 前端代码支持以下格式：
      // 1. HR:75 或 heartRate:75
      // 2. {"heartRate": 75} (JSON格式)
      // 3. 纯数字 75 (40-200之间)
      
      // 方式1：使用 HR: 前缀（推荐，简洁）
      Serial.print("HR:");
      Serial.println(Bpm_value);
      
      // 方式2：使用 JSON 格式（更规范，但数据量稍大）
      // Serial.print("{\"heartRate\":");
      // Serial.print(Bpm_value);
      // Serial.println("}");
      
      // 方式3：纯数字（最简单，但可能与其他数据混淆）
      // Serial.println(Bpm_value);
    }
  }
  
  // 如果没有检测到心跳，但之前有心率值，可以定期发送当前平均值
  // 这样可以保持前端的心率显示更新（可选）
  // 注意：这会增加串口数据量，如果不需要可以注释掉
  /*
  static unsigned long lastSendTime = 0;
  if (Bpm_value > 0 && millis() - lastSendTime > 2000) { // 每2秒发送一次
    Serial.print("HR:");
    Serial.println(Bpm_value);
    lastSendTime = millis();
  }
  */
}

