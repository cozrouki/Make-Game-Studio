---
name: urp-advanced-creator
description: "Unity 6 URP 심화 스킬. Forward+/Deferred 렌더링, 조명/그림자, Renderer Features, Render Graph, 포스트 프로세싱, Camera Stacking, GPU Resident Drawer, STP 등 Unity 6 URP 전체를 커버한다."
version: 1.0.0
source: "Introduction to the Universal Render Pipeline for advanced Unity creators (Unity 6 edition, Unity Technologies 2024)"
argument-hint: "topic='lighting' OR 'renderer-features' OR 'post-processing' OR 'camera-stacking' OR 'performance' OR 'shaders'"
disable-model-invocation: false
user-invocable: true
allowed-tools:
  - run_command
  - list_dir
  - write_to_file
---

# URP Advanced Creator (Unity 6)

## Overview
Unity 6 URP의 전체 렌더링 파이프라인을 다룬다.
Built-In → URP 마이그레이션, Forward+, 고급 조명, Renderer Features, Render Graph, 포스트 프로세싱 코드 제어, Camera Stacking, GPU Resident Drawer 등 고급 기능을 포함한다.

---

## When to Use
- Built-In Render Pipeline → URP 마이그레이션 시
- 렌더링 모드(Forward / Forward+ / Deferred) 선택 시
- 조명/그림자 품질 최적화가 필요할 때
- SSAO, Decals, Rendering Layers 적용 시
- 포스트 프로세싱을 코드로 제어할 때
- Camera Stacking(UI 카메라, 인벤토리 오버레이 등) 구현 시
- 커스텀 Renderer Feature / Render Pass 제작 시
- GPU Resident Drawer, STP 등 Unity 6 신기능 활용 시
- URP 성능 최적화 시

---

## 1. URP 프로젝트 설정

### 신규 프로젝트
- Unity Hub → **Universal Render Pipeline** 또는 **3D (URP)** 템플릿
- Color Space: Linear (자동 설정됨 — 조명 계산에 필수)

### 기존 Built-In 프로젝트 → URP 전환
```
1. Window > Package Manager > Unity Registry → Universal RP 설치
2. Project > Create > Rendering > URP Asset (with Universal Renderer)
3. Edit > Project Settings > Graphics > Scriptable Render Pipeline Settings에 URP Asset 지정
4. Window > Rendering > Render Pipeline Converter
   → Material 변환: Built-In → URP 자동 변환 (마젠타 오류 해결)
```

### URP 에셋 구조 (2개 파일)
```
UniversalRenderPipelineAsset  ← 품질/조명/그림자 설정
UniversalRenderPipelineAsset_Renderer  ← 렌더링 로직, Renderer Features
```

### 핵심 URP Asset 설정
| 설정 | 권장값 | 비고 |
|------|--------|------|
| Rendering Path | Forward+ | 다수 조명 씬 |
| HDR | ✅ ON | Bloom 등 HDR 효과 필요 |
| MSAA | 4x | PC/콘솔 |
| Shadow Distance | 씬 규모에 맞게 | 멀수록 비용↑ |
| Additional Lights | Per Pixel | 그림자 지원 |
| GPU Resident Drawer | Instanced Drawing | Unity 6, DrawCall 대폭 감소 |

---

## 2. 렌더링 모드 비교

| 기능 | Forward | Forward+ | Deferred |
|------|:-------:|:--------:|:--------:|
| 오브젝트당 실시간 조명 최대 수 | 9개 | **무제한** | **무제한** |
| 다수 조명 성능 | 낮음 | **높음** | 높음 |
| 투명 오브젝트 처리 | ✅ | ✅ | ❌ (별도 Forward pass) |
| 모바일 지원 | ✅ | ✅ | 제한적 |
| Normal 인코딩 손실 | 없음 | 없음 | 선택 가능 |
| MSAA | ✅ | ✅ | ❌ |
| 권장 상황 | 간단한 씬 | 복잡한 조명 씬 | 대규모 PC 씬 |

> **TikiProject 권장**: 다수 조명이 필요한 씬 → **Forward+**

---

## 3. 조명 시스템

### 조명 구조
```
URP 조명
├── Main Light (Directional Light)
│   ├── Sun Source: Window > Rendering > Lighting > Environment > Sun Source
│   ├── Shadow Resolution: 256 / 512 / 1024 / 2048 / 4096
│   └── Shadow Max Distance: 씬 단위 기준
└── Additional Lights (Point / Spot / Area)
    ├── Mode: Per Pixel (그림자 지원) / Per Vertex / Disabled
    └── Per Camera Limit: 데스크탑 256개, 모바일 32개
```

### 그림자 Cascade 설정
```
URP Asset > Shadows
├── Max Distance: 카메라로부터 그림자 최대 거리
├── Cascade Count: 1~4 (수록 품질↑, 비용↑)
└── Cascade Split: 비율로 각 Cascade 거리 조정

실용 설정 (PC):
- Max Distance: 50
- Cascade Count: 3
- Split: 0.07 / 0.2 / 0.45
```

### Adaptive Probe Volumes (APV) — Unity 6 권장
```
Light Probe 대안. 씬 형상 기반 자동 배치.

설정 방법:
1. Edit > Project Settings > Quality > Lighting > Light Probe System: Probe Volumes
2. Hierarchy > Light Probe Volume 추가 (Mode: Global)
3. Subdivisions: 1m / 3m / 9m / 27m
4. Generate Lighting (베이크)
5. Window > Analysis > Rendering Debugger > Probe Volumes로 확인
```

### SSAO (Screen Space Ambient Occlusion)
```
URP Renderer Data > Add Renderer Feature > Screen Space Ambient Occlusion

핵심 설정:
- Intensity: 1.0 (기본)
- Radius: 0.035
- Falloff Distance: 카메라 원거리 SSAO 비적용 거리 (성능 절감)
- After Opaque: ✅ (투명 오브젝트 제외)
```

### Decals (데칼)
```
URP Renderer Data > Add Renderer Feature > Decal

사용법:
1. Renderer Feature에 Decal 추가
2. Shader Graph > Decal Shader로 머티리얼 제작
3. Hierarchy > Rendering > URP Decal Projector 추가
4. Rendering Layers로 특정 메시에만 투영 가능

활용: 총흔, 발자국, 균열, 표지판
```

---

## 4. 포스트 프로세싱

### Volume 시스템
```
Default Volume  → Edit > Project Settings > Graphics > Volume (전역 기본값)
Global Volume   → 씬 전체 적용
Local Volume    → Box/Sphere Collider 진입 시 적용 (지역 효과)
URP Asset Volume → URP Asset별 기본값 (Unity 6 신기능)
```

### 포스트 프로세싱 적용 순서
```
1. Main Camera > Rendering > Post Processing: ✅ 활성화
2. Hierarchy > Create > Volume > Global Volume 생성
3. Volume Inspector > New Profile 생성
4. Add Override → 원하는 효과 추가
5. 각 효과 좌측 체크박스로 활성화 후 값 조정
```

### 효과 목록 & 모바일 호환성
| 효과 | 설명 | 모바일 |
|------|------|:------:|
| **Bloom** | 밝은 영역 발광 오버랩 | ✅ |
| **Vignette** | 화면 테두리 어둡게 | ✅ |
| **Color Adjustments** | 밝기/채도/대비 조정 | ✅ |
| **Color Grading** | 색감 LUT 적용 | ✅ |
| **Color Lookup** | 픽셀 색상 LUT 매핑 | ✅ |
| **Film Grain** | 필름 그레인 노이즈 | ✅ |
| **Depth of Field** | 카메라 피사계 심도 | 제한적 |
| **Motion Blur** | 움직임 블러 | 제한적 |
| **Lens Distortion** | 렌즈 왜곡 | ✅ |
| **Chromatic Aberration** | 색수차 | ✅ |
| **Panini Projection** | 파노라마 투영 왜곡 | ❌ |

### 포스트 프로세싱 코드 제어
```csharp
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public class PostProcessController : MonoBehaviour
{
    private Volume _volume;
    private Bloom _bloom;
    private Vignette _vignette;

    private void Awake()
    {
        _volume = GetComponent<Volume>();
        _volume.profile.TryGet(out _bloom);
        _volume.profile.TryGet(out _vignette);
    }

    // 피격 시 빨간 비네트 효과
    public void OnDamaged(float intensity)
    {
        if (_vignette != null)
        {
            _vignette.color.Override(Color.red);
            _vignette.intensity.Override(intensity);
        }
    }

    // Bloom 강도 조절 (보스 등장 연출 등)
    public void SetBloomIntensity(float value)
    {
        if (_bloom != null)
            _bloom.intensity.Override(value);
    }
}
```

---

## 5. Camera Stacking

### 개요
여러 카메라의 렌더 결과를 합성. UI 카메라, 인벤토리 오버레이, 다른 FOV 오브젝트 렌더 등에 사용.

### 설정 순서
```
1. 오버레이 카메라 생성 (Hierarchy > Camera)
   - Audio Listener 컴포넌트 제거
   - Inspector > Camera > Render Type: Overlay
2. 오버레이 전용 Layer 생성
3. 오버레이 카메라의 Rendering > Culling Mask: 해당 Layer만 선택
4. Main Camera의 Culling Mask에서 해당 Layer 제외
5. Main Camera > Stack > "+" → 오버레이 카메라 추가
```

### 코드로 Camera Stack 제어
```csharp
using UnityEngine;
using UnityEngine.Rendering.Universal;

public class CameraStackController : MonoBehaviour
{
    [SerializeField] private Camera overlayCamera;
    private UniversalAdditionalCameraData _cameraData;

    private void Awake()
    {
        _cameraData = GetComponent<UniversalAdditionalCameraData>();
    }

    public void AddOverlayCamera() =>
        _cameraData.cameraStack.Add(overlayCamera);

    public void RemoveOverlayCamera() =>
        _cameraData.cameraStack.Remove(overlayCamera);
}
```

---

## 6. Renderer Features & Render Graph

### Renderer Features
```
URP Renderer Data > Add Renderer Feature

내장 제공:
- Screen Space Ambient Occlusion (SSAO)
- Decal
- Render Objects   ← 특정 레이어 오브젝트 추가 렌더 (실루엣, X-ray 등)
- Full Screen Pass Renderer Feature ← 커스텀 포스트 프로세싱
- Screen Space Shadows

커스텀 Renderer Feature 예시 (캐릭터 X-ray 실루엣):
1. SeeBehind Layer 생성
2. Renderer Feature > Render Objects 추가
3. Filter: Layer Mask = SeeBehind
4. Override Material: 반투명 색상 머티리얼
5. Depth Test: Greater (벽 뒤 캐릭터 표시)
```

### Render Graph (Unity 6 — 커스텀 패스)
```csharp
// ScriptableRendererFeature 상속
public class CustomRenderFeature : ScriptableRendererFeature
{
    CustomRenderPass _pass;

    public override void Create()
    {
        _pass = new CustomRenderPass();
        _pass.renderPassEvent = RenderPassEvent.AfterRenderingOpaques;
    }

    public override void AddRenderPasses(ScriptableRenderer renderer, ref RenderingData renderingData)
    {
        renderer.EnqueuePass(_pass);
    }
}

// RenderGraph 기반 패스
class CustomRenderPass : ScriptableRenderPass
{
    public override void RecordRenderGraph(RenderGraph renderGraph, ContextContainer frameData)
    {
        using (var builder = renderGraph.AddRasterRenderPass<PassData>("CustomPass", out var passData))
        {
            // 리소스 선언 → 렌더그래프가 메모리 자동 관리
            var resourceData = frameData.Get<UniversalResourceData>();
            builder.SetRenderAttachment(resourceData.activeColorTexture, 0);
            builder.SetRenderFunc((PassData data, RasterGraphContext ctx) =>
            {
                // 렌더링 커맨드
            });
        }
    }
}
```

---

## 7. URP 커스텀 셰이더 (HLSL)

### 기본 구조 (URP Unlit)
```hlsl
Shader "CustomURP/Unlit"
{
    Properties { }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" }
        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings   { float4 positionHCS : SV_POSITION; };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                OUT.positionHCS = TransformObjectToHClip(IN.positionOS.xyz);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                return half4(1, 1, 1, 1); // 흰색
            }
            ENDHLSL
        }
    }
}
```

### SRP Batcher 호환 (필수)
```hlsl
// CBUFFER 블록 필수 — SRP Batcher 활성화 조건
CBUFFER_START(UnityPerMaterial)
    half4 _BaseColor;
    float _Smoothness;
CBUFFER_END
```

### URP 조명 접근 (Lambert)
```hlsl
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

// fragment shader 내부
Light mainLight = GetMainLight();
float NdotL = saturate(dot(normalWS, mainLight.direction));
float3 diffuse = mainLight.color * NdotL;
```

---

## 8. Unity 6 신기능

### GPU Resident Drawer
```
URP Asset > Rendering > GPU Resident Drawer: Instanced Drawing

효과: DrawCall 대폭 감소 (예: 3569 → 506 batches)
GPU Occlusion Culling도 함께 활성화됨

확인: Window > Analysis > Rendering Debugger
      > GPU Resident Drawer > Occlusion Test Overlay (히트맵)
```

### STP (Spatial-Temporal Post-Processing)
```
Unity의 자체 Super Resolution — 모바일/콘솔/PC 전 플랫폼 지원
(FSR, DLSS와 달리 하드웨어 벤더 독립적)

URP Asset > Quality > Upscaling Filter: Spatial-Temporal Post-Processing
Render Scale: 0.5 설정 후 STP 활성화 → 네이티브 해상도 품질 유지
```

### HDR Output (Unity 6 모바일 추가)
```
지원 플랫폼 (Unity 6):
- iOS 16+ / iPadOS 16+
- Android 14+ (Galaxy S24 등)

활성화:
1. Project Settings > Player > Other Settings > Use HDR Display Output: ✅
2. URP Asset > Quality > HDR: ✅
3. Rendering Debugger > Lighting > HDR Debug Mode로 확인
```

---

## 9. 성능 최적화

### 조명 최적화
```
✅ 베이크 조명 적극 활용
   - 동적 오브젝트: Light Probe / APV로 GI 샘플링
   - 정적 오브젝트: Baked GI (Diffuse 전용)
   - 직접 조명은 Real-time, GI는 Baked 혼합 권장

✅ Additional Lights Per Camera 제한
   - 데스크탑: 최대 256개
   - 모바일: 최대 32개

✅ Shadow Cascade 조정
   - 모바일: Cascade 1~2개
   - 데스크탑: Cascade 3~4개

❌ 모든 조명에 Per Pixel Shadow 금지
❌ Shadow Max Distance 과도하게 크게 설정 금지
```

### 렌더링 최적화
```
✅ GPU Resident Drawer: Instanced Drawing 활성화
✅ GPU Occlusion Culling 활성화
✅ STP로 Render Scale 낮추기 (0.5~0.75)
✅ MSAA: 모바일 비활성화 또는 2x
✅ Forward+ 사용 (다수 조명 씬)
✅ Reflection Probe: 베이크 + 범위 최소화
```

### 프로파일링 도구
```
Window > Analysis > Profiler          → 전체 성능 분석
Window > Analysis > Frame Debugger    → 렌더 패스별 드로우 콜 확인
Window > Analysis > Rendering Debugger → URP 전용 디버깅
  ├── Lighting (Shadow, APV 시각화)
  ├── GPU Resident Drawer (Occlusion 히트맵)
  └── Rendering (DrawCall, Batches 통계)
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    URP RENDERING PIPELINE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [URP Asset]                [Renderer Data]                     │
│  Quality/Lighting/Shadow ←→ Renderer Features (SSAO, Decal..)  │
│          │                          │                           │
│          ▼                          ▼                           │
│     [Rendering Mode]          [Render Graph]                    │
│  Forward / Forward+ / Deferred   Custom Passes                  │
│          │                                                      │
│  [Lighting]                                                     │
│  Main Light + Additional Lights                                 │
│  ├── Shadow Cascades                                            │
│  ├── Light Probes / APV                                         │
│  └── SSAO / Decals / Rendering Layers                           │
│          │                                                      │
│  [Camera Stack]                                                 │
│  Base Camera → [Overlay Camera 1] → [Overlay Camera 2]          │
│          │                                                      │
│  [Post-Processing Volumes]                                      │
│  Default → Global → Local (우선순위 순)                          │
│  Bloom / Vignette / DOF / Motion Blur / Color Grading           │
│          │                                                      │
│  [Unity 6 신기능]                                               │
│  GPU Resident Drawer → GPU Occlusion Culling → STP              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Few-Shot Examples

### Example 1: Built-In → URP 마이그레이션
**User**: "기존 Built-In 프로젝트를 URP로 전환하고 싶어."

**Agent**:
```
1. Package Manager > Universal RP 설치
2. URP Asset 생성 (Create > Rendering > URP Asset)
3. Project Settings > Graphics > SRP Settings에 Asset 지정
4. Window > Rendering > Render Pipeline Converter 실행
   - Rendering Settings Converter: ✅
   - Material Upgrade: ✅
   → Convert 버튼 클릭 (마젠타 머티리얼 자동 변환)
주의: Custom Shader는 수동 HLSL 변환 필요
```

### Example 2: Camera Stacking으로 UI 카메라 분리
**User**: "UI가 항상 앞에 보이도록 별도 카메라로 렌더하고 싶어."

**Agent**:
```
1. UICamera GameObject 생성
2. Camera > Render Type: Overlay
3. Culling Mask: UI Layer만 선택
4. Audio Listener 제거
5. Main Camera > Culling Mask에서 UI Layer 제외
6. Main Camera > Stack > "+" > UICamera 추가
→ UI가 별도 패스로 렌더, Main Camera와 합성
```

### Example 3: 피격 시 붉은 비네트 효과
**User**: "플레이어가 피격될 때 화면이 빨갛게 되는 효과가 필요해."

**Agent**:
```
1. Main Camera에 Global Volume 추가
2. Profile에 Vignette Override 추가
3. PostProcessController.cs 부착
4. GameManager에서 OnDamaged 호출:
   postProcessController.OnDamaged(0.6f);
→ 위 코드 섹션 4 참조
5. DOTween으로 intensity를 0.6 → 0으로 서서히 복구
```

### Example 4: GPU Resident Drawer로 DrawCall 감소
**User**: "씬에 오브젝트가 많아서 DrawCall이 너무 높아."

**Agent**:
```
1. URP Asset > Rendering > GPU Resident Drawer: Instanced Drawing
2. GPU Occlusion Culling: ✅ 활성화
3. Window > Analysis > Rendering Debugger > GPU Resident Drawer
   > Occlusion Test Overlay로 효과 확인
주의: 스키닝 메시(Skinned Mesh Renderer)는 GPU Resident Drawer 미지원
```

---

## Related Skills
- `@shader-graph-expert` - Shader Graph로 커스텀 머티리얼
- `@lighting-post-processing` - 조명/포스트 프로세싱 기초
- `@2d-art-animation-lighting` - URP 2D Renderer
- `@mobile-optimization` - 모바일 URP 최적화
- `@dots-system-architect` - GPU 기반 성능 극한 최적화
