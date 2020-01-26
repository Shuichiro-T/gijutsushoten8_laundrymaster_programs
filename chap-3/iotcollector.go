package iotcollector

import (
    "context"
    "encoding/json"
    "log"
    "os"
    "time"

    //BiqQueryを操作するのに必要なライブラリ
    "cloud.google.com/go/bigquery"
    "cloud.google.com/go/civil"
)

//Pub/Subから受け取るメッセージを格納する構造体
type PubSubMessage struct {
    Data []byte `json:"data"`
}

//メッセージの中身を格納し、BigQueryにデータを追加するための
//構造体、タグで変数とキーを紐づける
type Info struct {
    ID             int      `json:"ID" bigquery:"ID"`
    LocationLogi   float64  `json:"LOCATION_LONGI" bigquery:"LOCATION_LONGI"`
    LocationLati   float64  `json:"LOCATION_LATI" bigquery:"LOCATION_LATI"`
    DeviceDatetime civil.DateTime `json:"DEVICE_DATETIME" bigquery:"DEVICE_DATETIME"`
    Pressure       float64  `json:"PRESSURE" bigquery:"PRESSURE"`
    Temperature    float64  `json:"TEMPERATURE" bigquery:"TEMPERATURE"`
    Humidity       float64   `json:"HUMIDITY" bigquery:"HUMIDITY"`
    Timestamp      time.Time `bigquery:"TIMESTAMP"`
}


//Pub/Subからメッセージを受信した時に実行される
func CollectDeviceData(ctx context.Context, m PubSubMessage) error {
    var i Info

    //json形式のメッセージを構造体へ格納する
    err := json.Unmarshal(m.Data, &i)

    //エラー時はエラーの型とエラー内容をLoggingへ出力する
    if err != nil {
        log.Printf("メッセージ変換エラー　Error:%T message: %v", err, err)
        return nil
    }

    //BigQueryにデータを追加する関数を呼び出す
    InsertBigQuery(&ctx, &i)

    return nil
}

//BigQueryにデータを追加する関数を定義する
func InsertBigQuery(ctx *context.Context, i *Info) {

    //プロジェクトIDを取得する
    projectID := os.Getenv("GCP_PROJECT")

    //BigQueryを操作するクライアントを作成する、エラーの場合はLoggingへ出力する
    client, err := bigquery.NewClient(*ctx, projectID)
    if err != nil {
        log.Printf("BigQuery接続エラー　Error:%T message: %v", err, err)
        return
    }

    //確実にクライアントを閉じるようにする
    defer client.Close()

    //クライアントからテーブルを操作するためのアップローダーを取得する
    u := client.Dataset("BME280").Table("ENV_DATA").Uploader()

    //現在時刻を構造体へ格納する
    i.Timestamp = time.Now()

    items := []Info{*i}

    //テーブルへデータの追加を行う、エラーの場合はLoggingへ出力する
    err = u.Put(*ctx, items)
    if err != nil {
        log.Printf("データ書き込みエラー　Error:%T message: %v", err, err)
        return
    }
}
