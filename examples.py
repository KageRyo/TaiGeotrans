"""
TaiGeotrans 使用範例

展示主要功能的示範程式碼。
"""

from taigeotrans import TaiGeotrans


def example_single_geocode():
    """範例 1：單一地址地理編碼"""
    print("=" * 60)
    print("範例 1：單一地址地理編碼")
    print("=" * 60)
    
    converter = TaiGeotrans()
    
    # 查詢台北 101
    result = converter.geocode("台北市信義區信義路五段7號")
    
    print(f"輸入地址: {result.input_address}")
    print(f"TWD97 座標: X={result.twd97_x:.2f}, Y={result.twd97_y:.2f}")
    print(f"WGS84 座標: 經度={result.wgs84_lon}, 緯度={result.wgs84_lat}")
    print(f"狀態: {result.status}")
    print(f"信心度: {result.confidence}")
    print(f"匹配地址: {result.matched_address}")
    print()


def example_coordinate_transform():
    """範例 2：座標轉換"""
    print("=" * 60)
    print("範例 2：WGS84 → TWD97 座標轉換")
    print("=" * 60)
    
    converter = TaiGeotrans()
    
    # 台北市政府座標（WGS84）
    lon, lat = 121.5654, 25.0330
    result = converter.transform_lonlat(lon, lat)
    
    print(f"輸入 WGS84: 經度={lon}, 緯度={lat}")
    print(f"輸出 TWD97: X={result.twd97_x:.2f}, Y={result.twd97_y:.2f}")
    print(f"狀態: {result.status}")
    print(f"在台灣範圍內: {result.is_in_taiwan_bounds()}")
    print()


def example_batch_geocode():
    """範例 3：批量地址地理編碼"""
    print("=" * 60)
    print("範例 3：批量地址地理編碼")
    print("=" * 60)
    
    converter = TaiGeotrans()
    
    addresses = [
        "台北市信義區市府路1號",
        "台北市中山區中山北路二段48巷7號",
        "高雄市新興區中正三路25號",
        "台中市西區公益路155號"
    ]
    
    # 批量處理（顯示進度條）
    results = converter.batch_geocode(addresses, show_progress=True)
    
    # 顯示結果
    print("\n結果摘要:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.input_address}")
        print(f"   TWD97: ({result.twd97_x:.2f}, {result.twd97_y:.2f})")
        print(f"   狀態: {result.status}")
    print()


def example_batch_transform():
    """範例 4：批量座標轉換"""
    print("=" * 60)
    print("範例 4：批量座標轉換")
    print("=" * 60)
    
    converter = TaiGeotrans()
    
    # 台灣主要城市座標（WGS84）
    coords = [
        (121.5654, 25.0330),  # 台北
        (120.3014, 22.6273),  # 高雄
        (120.6736, 24.1477),  # 台中
        (121.0, 24.8),        # 新竹
    ]
    
    results = converter.batch_transform_lonlat(coords, show_progress=True)
    
    print("\n轉換結果:")
    cities = ["台北", "高雄", "台中", "新竹"]
    for city, result in zip(cities, results):
        print(f"{city}: TWD97=({result.twd97_x:.2f}, {result.twd97_y:.2f})")
    print()


def example_dataframe_output():
    """範例 5：輸出為 pandas DataFrame"""
    print("=" * 60)
    print("範例 5：輸出為 pandas DataFrame")
    print("=" * 60)
    
    converter = TaiGeotrans()
    
    addresses = [
        "台北市信義區市府路1號",
        "高雄市新興區中正三路25號",
    ]
    
    # 轉換為 DataFrame
    df = converter.batch_geocode_to_dataframe(addresses, show_progress=False)
    
    # 顯示部分欄位
    print(df[['input_address', 'twd97_x', 'twd97_y', 'status', 'confidence']])
    print()
    
    # 儲存為 CSV
    # df.to_csv('results.csv', index=False, encoding='utf-8-sig')
    # print("已儲存至 results.csv")


def example_geojson_output():
    """範例 6：輸出為 GeoJSON"""
    print("=" * 60)
    print("範例 6：輸出為 GeoJSON")
    print("=" * 60)
    
    converter = TaiGeotrans()
    
    coords = [
        (121.5654, 25.0330),  # 台北
        (120.3014, 22.6273),  # 高雄
    ]
    
    results = converter.batch_transform_lonlat(coords, show_progress=False)
    geojson = converter.to_geojson(results)
    
    print(f"GeoJSON 類型: {geojson['type']}")
    print(f"特徵數量: {len(geojson['features'])}")
    print(f"第一個特徵:")
    print(f"  座標: {geojson['features'][0]['geometry']['coordinates']}")
    print(f"  TWD97: X={geojson['features'][0]['properties']['twd97_x']:.2f}, "
          f"Y={geojson['features'][0]['properties']['twd97_y']:.2f}")
    print()
    
    # 儲存為 GeoJSON 檔案
    # import json
    # with open('results.geojson', 'w', encoding='utf-8') as f:
    #     json.dump(geojson, f, ensure_ascii=False, indent=2)
    # print("已儲存至 results.geojson")


if __name__ == "__main__":
    # 執行所有範例
    example_single_geocode()
    example_coordinate_transform()
    example_batch_geocode()
    example_batch_transform()
    example_dataframe_output()
    example_geojson_output()
    
    print("=" * 60)
    print("所有範例執行完成！")
    print("=" * 60)
