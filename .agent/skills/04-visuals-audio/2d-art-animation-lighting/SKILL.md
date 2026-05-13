---
name: 2d-art-animation-lighting
description: "Unity 6.3 LTS 기반 2D 게임 아트, 스켈레탈 애니메이션, 조명 시스템 전문 스킬. URP 2D Renderer, Sprite 워크플로우, 2D Lighting, VFX까지 아우르는 종합 2D 비주얼 스킬."
version: 1.0.0
source: "Unity 6.3 LTS - 2D game art, animation, and lighting for artists (e-book)"
argument-hint: "topic='sprite' OR 'animation' OR 'lighting' OR 'tilemap' OR 'vfx'"
disable-model-invocation: false
user-invocable: true
allowed-tools:
  - run_command
  - list_dir
  - write_to_file
---

# 2D Art, Animation & Lighting (Unity 6.3 LTS)

## Overview
Unity 6.3 LTS 공식 e-book 기반. URP 2D Renderer를 사용하는 2D 게임의 아트 파이프라인 전체를 커버한다.
스프라이트 임포트 → 타일맵 → 스켈레탈 애니메이션 → 2D 조명 → VFX → 최적화 순서로 작업한다.

---

## When to Use
- 2D 프로젝트 초기 URP 세팅이 필요할 때
- 스프라이트 임포트, 슬라이싱, Sprite Editor 작업 시
- 타일맵(Tilemap) 기반 레벨 제작 시
- 2D 캐릭터 리깅, 스켈레탈 애니메이션, IK 구현 시
- 2D 조명(Normal Map, Mask Map, Shadow) 적용 시
- 2D VFX(Particle System, VFX Graph, Shader Graph) 제작 시
- 2D 성능 최적화가 필요할 때

---

## 1. URP 2D 프로젝트 세팅

### 프로젝트 생성
- Unity Hub → **Universal 2D** 템플릿 선택 (Unity 6.3 LTS)
- 필수 패키지: `2D Tilemap Editor`, `2D Tilemap Extras`, `2D Animation`, `2D PSD Importer`

### URP 2D Renderer 핵심 설정
```
Project Settings > Graphics > URP Asset
├── 2D Renderer Data (별도 Asset)
│   ├── Renderer Type: 2D Renderer
│   ├── HDR Emulation Scale: 1.0 (조명 강도)
│   └── Light Blend Styles: Additive / Multiply / Subtractive
└── Quality Settings
    ├── Anti Aliasing: 4x MSAA (권장)
    └── Render Scale: 1.0
```

### 카메라 설정 (필수)
- Camera > Projection: **Orthographic**
- Environment > Background Type: **Solid Color** (2D는 Skybox 불필요)

---

## 2. 스프라이트(Sprite) 워크플로우

### 임포트 설정 체크리스트
| 설정 | 권장값 | 비고 |
|------|--------|------|
| Texture Type | Sprite (2D and UI) | 기본 |
| Sprite Mode | Single / Multiple | 스프라이트시트는 Multiple |
| Pixels Per Unit | 100 | 프로젝트 통일 필수 |
| Filter Mode | Point (no filter) | 픽셀아트 / Bilinear: 일반 |
| Compression | Sprite | 플랫폼별 자동 압축 |
| Generate Mip Maps | ❌ OFF | 2D에서는 불필요 |

### Sprite Editor 주요 기능
```
Sprite Editor
├── Slice          → 자동/격자/커스텀 슬라이싱
├── Custom Outline → 불투명 픽셀 기준 메시 최적화 (성능↑)
├── Custom Physics Shape → 충돌 영역 커스텀
├── Secondary Textures → Normal Map / Mask Map 연결
└── Skinning Editor → 스켈레탈 애니메이션 리깅
```

### Sprite Renderer 설정
- **Sorting Layer + Order in Layer** → 드로우 순서 결정
- **Flip X/Y** → 방향 전환 (Scale 음수 대신 사용)
- **Sprite Mask** → 마스크 영역 기반 잘라내기

### Sprite Library & Sprite Swap
```csharp
// Sprite Swap 런타임 변경
[SerializeField] private SpriteLibraryAsset libraryAsset;
private SpriteLibrary _spriteLibrary;

private void Awake()
{
    _spriteLibrary = GetComponent<SpriteLibrary>();
}

public void SwapCharacterSkin(string categoryName, string labelName)
{
    // SpriteLibraryAsset의 카테고리/라벨로 스프라이트 교체
    _spriteLibrary.spriteLibraryAsset = libraryAsset;
    var resolver = GetComponentInChildren<SpriteResolver>();
    resolver.SetCategoryAndLabel(categoryName, labelName);
}
```

---

## 3. 2D 타일맵(Tilemap)

### 구조
```
Grid (GameObject)
└── Tilemap (Component)
    ├── Tilemap Renderer (정렬, 레이어)
    └── Tilemap Collider 2D (선택)
```

### 타일 팔레트 설정
- Window > 2D > Tile Palette 열기
- Brush: 기본 / Line / Box / Fill 브러시 사용
- **Rule Tile**: 인접 타일 규칙 기반 자동 선택 (벽/바닥 전환)
- **Random Tile**: 변형 타일 랜덤 배치

### 성능: Tilemap Chunk 최적화
- Tilemap은 내부적으로 **Chunk** 단위로 렌더링
- Chunk Size 조정: Tilemap Renderer > Chunk Culling Bounds
- 멀리 있는 청크는 자동 Culling → 카메라 범위만 렌더링

---

## 4. 2D 스켈레탈 애니메이션

### 워크플로우 순서
```
1. PSD Importer로 레이어 분리 임포트 (Photoshop → Unity)
   └── 또는 Sprite Editor로 수동 슬라이싱
2. Skinning Editor에서 스켈레톤 생성
   ├── Create Bone 도구로 뼈대 배치
   ├── Auto Geometry로 스프라이트 메시 생성
   └── Weight Slider로 본 웨이트 조정
3. Animator Controller 설정
4. Animation Window에서 키프레임 설정
```

### 2D IK (Inverse Kinematics)
```csharp
// IK Manager 2D 컴포넌트 필요 (2D Animation 패키지)
// Chain (CCD) IK: 발이 지면에 닿도록 자동 계산
// Limb IK: 팔/다리 2본 IK (가장 일반적)

// 런타임 IK 타겟 변경
[SerializeField] private Transform ikTarget;
private IKManager2D _ikManager;

private void Awake()
{
    _ikManager = GetComponent<IKManager2D>();
}

public void SetFootTarget(Vector3 worldPosition)
{
    ikTarget.position = worldPosition;
}
```

### 애니메이션 최적화
- **Optimize Game Objects**: Animator > Culling Mode → Always Animate / Cull Update Transforms
- **Animation Compression**: Loop Time 체크, 불필요한 커브 제거
- 화면 밖 캐릭터: Culling Mode = Cull Completely

---

## 5. 2D 조명 시스템

### 조명 타입
| Light Type | 용도 |
|------------|------|
| **Global Light 2D** | 전체 환경 기본 밝기 |
| **Freeform Light 2D** | 자유 형태 커스텀 영역 조명 |
| **Point Light 2D** | 점광원 (torch, lamp) |
| **Spot Light 2D** | 방향성 스포트라이트 |
| **Parametric Light 2D** | 다각형 형태 조명 |

### Blend Style 설정
```
Light Blend Styles (2D Renderer Data)
├── Additive   → 색상 더하기 (화염, 마법)
├── Multiply   → 색상 곱하기 (그림자, 어두운 영역)
└── Subtractive → 색상 빼기 (역광, 특수 효과)
```

### Secondary Textures (Normal Map & Mask Map)
```
Sprite Editor > Secondary Textures
├── _NormalMap  → 법선 맵 (3D 입체감)
└── _MaskMap    → R:Metallic G:AO B:Detail A:Smoothness
```

**Normal Map 생성 과정:**
1. 원본 스프라이트 → Sprite Lit Shader Graph에서 SpriteNormalLit 사용
2. 외부 툴: Sprite DLight / SpriteLamp / Aseprite 플러그인
3. 또는 Shader Graph에서 Color Sampling으로 직접 제작

### 2D 그림자
```
Shadow Caster 2D 컴포넌트
├── Use Renderer Silhouette: 스프라이트 외곽선으로 자동 그림자
├── Self Shadows: 자기 자신에게도 그림자
└── Casting Source: Composite Shadow (복합 오브젝트)

Infinite Shadows → Global Light의 Shadow Distance로 조절
Blob Shadows     → 단순 원형 텍스처 스프라이트 (저성능 기기용)
```

### 낮/밤 사이클 구현
```csharp
[SerializeField] private Light2D globalLight;
[SerializeField] private Gradient dayNightGradient;
[SerializeField] private float cycleDuration = 120f; // 초

private void Update()
{
    float t = Mathf.PingPong(Time.time / cycleDuration, 1f);
    globalLight.color = dayNightGradient.Evaluate(t);
    globalLight.intensity = Mathf.Lerp(0.1f, 1.2f, t);
}
```

---

## 6. 2D VFX

### VFX 제작 방법 비교
| 방법 | 적합한 상황 | 성능 |
|------|-------------|------|
| **Frame-by-Frame** | 폭발, 특수 연출 | 중간 |
| **Particle System (Shuriken)** | 불꽃, 연기, 비 | 중간 |
| **VFX Graph** | 대량 파티클, GPU 기반 | 고성능 |
| **Shader Graph** | 왜곡, 용해, 흐름 효과 | 가변적 |

### Sprite Lit Shader Graph (2D 전용)
```
Sprite Lit Graph
├── Vertex: Position 조작 (파도, 흔들림)
├── Fragment
│   ├── Base Color ← 텍스처 Sample
│   ├── Normal Map ← Secondary Texture
│   ├── Mask Map   ← Metallic/AO/Smoothness
│   └── Emission   ← HDR 발광 효과
```

### Flow Map (흐름 효과)
```
UV.x += FlowMap.r * _FlowSpeed * Time
UV.y += FlowMap.g * _FlowSpeed * Time
→ 물, 용암, 마법 흐름 표현
```

### 2D 포스트 프로세싱 (URP Volume)
```
Volume 컴포넌트 (Camera에 추가)
├── Bloom         → 발광 오버랩
├── Vignette      → 화면 테두리 어둡게
├── Color Grading → 색감 보정
├── Chromatic Aberration → 색수차
└── Film Grain    → 필름 그레인 노이즈

Local Volume → 특정 영역 진입 시 효과 변경
```

---

## 7. 성능 최적화

### 스프라이트 최적화
- ✅ Sprite Atlas 사용 → Draw Call 감소
- ✅ Custom Outline → 투명 픽셀 렌더 제거
- ✅ Mip Map 비활성화 (2D에서 불필요)
- ✅ Compression: ETC2(Android), ASTC(iOS)
- ❌ 과도한 Sorting Layer 중첩 금지

### 조명 최적화
- ✅ Light Culling: 조명의 Target Sorting Layers 한정
- ✅ Shadow Strength 낮추기 (연산 비용)
- ✅ Global Light는 1개만 사용
- ❌ 모든 오브젝트에 Normal Map 적용 금지 (저사양 기기)

### 애니메이션 최적화
- ✅ Animator Culling Mode: Cull Completely (화면 밖)
- ✅ 애니메이션 클립 Loop Time 최소화
- ✅ GPU Skinning 활성화 (Project Settings > Player)

### 타일맵 최적화
- ✅ Tilemap Renderer: Chunk mode 사용
- ✅ 정적 타일은 Static Batching
- ✅ Composite Collider 2D로 충돌 최적화

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    2D ART PIPELINE                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [Source Art]                                                │
│  PSD / PNG  ──→  Sprite Importer  ──→  Sprite Atlas          │
│                         │                                    │
│                  ┌──────┴──────┐                             │
│                  ↓             ↓                             │
│           [Sprite Editor]  [PSD Importer]                    │
│            Slice/Outline    Layer Split                      │
│                  │                                           │
│          ┌───────┼──────────┐                                │
│          ↓       ↓          ↓                                │
│      [Tilemap] [Sprite  [Skinning Editor]                    │
│               Renderer]  Rig + Weights                       │
│                              │                               │
│                       [Animator Controller]                  │
│                        IK / Sprite Swap                      │
│                                                              │
│  [Rendering]                                                 │
│  URP 2D Renderer                                             │
│  ├── 2D Lights (Point/Spot/Global/Freeform)                  │
│  ├── Normal Map + Mask Map (Secondary Textures)              │
│  ├── Shadow Caster 2D                                        │
│  └── Post-Processing Volume (Bloom, Color Grade)             │
│                                                              │
│  [VFX]                                                       │
│  Particle System / VFX Graph / Shader Graph                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Few-Shot Examples

### Example 1: Normal Map이 적용된 2D 캐릭터 조명
**User**: "2D 캐릭터에 입체적인 조명 효과를 주고 싶어."

**Agent**:
```
1. Sprite Editor > Secondary Textures
   - _NormalMap 슬롯에 법선 맵 텍스처 연결
2. Material: Sprite-Lit-Default 사용
3. 씬에 Point Light 2D 추가
   - Blend Style: Additive
   - Intensity: 1.5
   - Outer Radius: 5
4. 캐릭터 Sprite Renderer > Material에 Sprite-Lit-Default 적용
→ 조명 방향에 따라 캐릭터 표면이 입체적으로 변화
```

### Example 2: Rule Tile로 자동 벽 타일맵
**User**: "벽과 바닥이 자동으로 연결되는 타일맵이 필요해."

**Agent**:
```
1. Project > Create > 2D > Tiles > Rule Tile 생성
2. Rule Tile 인스펙터에서 규칙 추가:
   - 위/아래/좌/우 이웃 타일 조건 설정
   - 각 조건 조합에 맞는 스프라이트 지정
3. Tile Palette에 Rule Tile 등록
4. 페인트 → 자동으로 코너/가장자리/내부 타일 전환
```

### Example 3: 낮/밤 사이클
**User**: "시간에 따라 밝기가 변하는 낮밤 사이클 구현해줘."

**Agent**:
```
DayNightController.cs 생성
- Global Light 2D 참조
- Gradient로 시간대별 색온도 설정
  (낮: 흰색, 노을: 주황, 밤: 남색)
- Update()에서 Mathf.PingPong으로 주기 계산
- globalLight.color / intensity 업데이트
```
→ 위 코드 섹션 5 참조

---

## Related Skills
- `@shader-graph-expert` - 커스텀 Sprite Shader 제작
- `@vfx-graph-shuriken` - 2D 파티클 이펙트
- `@lighting-post-processing` - URP 포스트 프로세싱 심화
- `@mobile-optimization` - 2D 모바일 최적화
- `@procedural-animation-ik` - 고급 IK 시스템
