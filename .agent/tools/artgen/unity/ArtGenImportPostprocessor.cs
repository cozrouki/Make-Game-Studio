// artgen 파이프라인 — 승격된 생성 이미지에 TextureImporter 설정을 자동 적용한다.
// 설정 출처: <프로젝트 루트>/production/artgen/import-map.json (artgen.py promote 가 기록)
// 설계 문서: .agent/tools/artgen/README.md §Unity 임포트
//
// 설치: /ko-art-gen 이 최초 승격 시 Assets/ArtGen/Editor/ 로 복사한다 (Editor 전용 asmdef 포함).
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace ArtGen.Editor
{
    public sealed class ArtGenImportPostprocessor : AssetPostprocessor
    {
        private const string ImportMapRelativePath = "production/artgen/import-map.json";

        [Serializable]
        private sealed class ImportMap
        {
            public int version;
            public List<Entry> entries = new List<Entry>();
        }

        // JsonUtility 는 필드 이름으로 매핑한다 — artgen_lib/request.py IMPORT_DEFAULTS 와 이름을 맞출 것
        [Serializable]
        private sealed class Entry
        {
            public string path;
            public string assetId;
            public string sourceSha256;
            public string textureType;
            public string spriteMode;
            public float pixelsPerUnit;
            public string filterMode;
            public int maxSize;
            public string compression;
            public bool mipmaps;
            public string wrapMode;
            public bool alphaIsTransparency;
            public bool sRGB;
        }

        private static Dictionary<string, Entry> s_entries;
        private static DateTime s_loadedWriteTime;

        private void OnPreprocessTexture()
        {
            Entry entry = Find(assetPath);
            if (entry == null)
            {
                return;
            }

            var importer = (TextureImporter)assetImporter;
            importer.textureType = ParseEnum(entry.textureType, TextureImporterType.Sprite, entry);
            if (importer.textureType == TextureImporterType.Sprite)
            {
                importer.spriteImportMode = ParseEnum(entry.spriteMode, SpriteImportMode.Single, entry);
                importer.spritePixelsPerUnit = entry.pixelsPerUnit > 0f ? entry.pixelsPerUnit : 100f;
            }

            importer.filterMode = ParseEnum(entry.filterMode, FilterMode.Bilinear, entry);
            importer.wrapMode = ParseEnum(entry.wrapMode, TextureWrapMode.Clamp, entry);
            importer.mipmapEnabled = entry.mipmaps;
            importer.alphaIsTransparency = entry.alphaIsTransparency;
            importer.sRGBTexture = entry.sRGB;
            if (entry.maxSize > 0)
            {
                importer.maxTextureSize = entry.maxSize;
            }

            importer.textureCompression = ParseCompression(entry.compression, entry);
        }

        private static Entry Find(string path)
        {
            string mapPath = Path.Combine(Directory.GetParent(Application.dataPath).FullName, ImportMapRelativePath);
            if (!File.Exists(mapPath))
            {
                return null;
            }

            // 임포트마다 디스크를 읽지 않도록 수정 시각 기준으로 캐싱
            DateTime writeTime = File.GetLastWriteTimeUtc(mapPath);
            if (s_entries == null || writeTime != s_loadedWriteTime)
            {
                s_entries = new Dictionary<string, Entry>(StringComparer.OrdinalIgnoreCase);
                try
                {
                    ImportMap map = JsonUtility.FromJson<ImportMap>(File.ReadAllText(mapPath));
                    if (map != null && map.entries != null)
                    {
                        foreach (Entry e in map.entries)
                        {
                            if (!string.IsNullOrEmpty(e.path))
                            {
                                s_entries[e.path] = e;
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    Debug.LogWarning($"[ArtGen] import-map.json 파싱 실패 — 설정 미적용: {ex.Message}");
                }

                s_loadedWriteTime = writeTime;
            }

            return s_entries.TryGetValue(path, out Entry found) ? found : null;
        }

        private static T ParseEnum<T>(string value, T fallback, Entry entry) where T : struct
        {
            if (string.IsNullOrEmpty(value))
            {
                return fallback;
            }

            if (Enum.TryParse(value, true, out T parsed))
            {
                return parsed;
            }

            Debug.LogWarning($"[ArtGen] {entry.assetId} {entry.path}: 알 수 없는 {typeof(T).Name} '{value}' — {fallback} 사용");
            return fallback;
        }

        private static TextureImporterCompression ParseCompression(string value, Entry entry)
        {
            switch (value)
            {
                case "None": return TextureImporterCompression.Uncompressed;
                case "LowQuality": return TextureImporterCompression.CompressedLQ;
                case "HighQuality": return TextureImporterCompression.CompressedHQ;
                case "Normal":
                case null:
                case "":
                    return TextureImporterCompression.Compressed;
                default:
                    Debug.LogWarning($"[ArtGen] {entry.assetId} {entry.path}: 알 수 없는 compression '{value}' — Normal 사용");
                    return TextureImporterCompression.Compressed;
            }
        }
    }
}
