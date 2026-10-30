# 좋은 테스트 · 나쁜 테스트 (Unity C# · NUnit)

## 좋은 테스트 — 공개 인터페이스로 동작 검증

```csharp
// ✅ 관찰 가능한 동작을 시험한다
[Test]
public void Respawn_OnEscapeFloor_PicksNearestElevatorWaitPoint()
{
    var policy = new RespawnPolicy(escapeFloorY: 20f, tolerance: 1.75f);
    var near = new Vector3(2f, 20f, 0f);
    var far = new Vector3(30f, 20f, 0f);

    var spawn = policy.Pick(playerPos: new Vector3(0f, 20.5f, 0f),
                            elevatorPoints: new[] { far, near });

    Assert.AreEqual(near, spawn);
}
```

특징:

- 호출자 · 플레이어가 신경 쓰는 동작을 시험한다
- 공개 API 만 쓴다
- 내부 리팩터링에 살아남는다
- 어떻게(HOW)가 아니라 무엇(WHAT)을 말한다
- 테스트 하나에 논리적 단언 하나

## 나쁜 테스트

**구현 세부에 묶인 테스트**

```csharp
// ❌ 내부 협력 객체 호출을 검증한다
[Test]
public void Respawn_CallsDistanceCalculatorTwice()
{
    var calc = new SpyDistanceCalculator();
    new RespawnPolicy(calc).Pick(...);
    Assert.AreEqual(2, calc.CallCount);
}
```

경고 신호:

- 내부 협력 객체를 대역으로 바꿈
- private 메서드를 리플렉션으로 시험
- 호출 횟수 · 순서를 단언
- 동작은 그대로인데 리팩터링하면 깨짐
- 테스트 이름이 무엇이 아니라 어떻게를 설명
- 인터페이스가 아닌 옆길로 검증

```csharp
// ❌ 인터페이스를 우회해 검증한다 — 저장 파일을 직접 읽음
[Test]
public void Save_WritesJsonFile()
{
    saveSystem.Save(slot: 0, state);
    var json = File.ReadAllText(Path.Combine(dir, "slot0.json"));
    StringAssert.Contains("\"level\":3", json);
}

// ✅ 인터페이스로 검증한다 — 저장한 것을 다시 불러옴
[Test]
public void Save_ThenLoad_RestoresLevel()
{
    saveSystem.Save(slot: 0, new GameState { Level = 3 });
    Assert.AreEqual(3, saveSystem.Load(slot: 0).Level);
}
```

**동어반복 테스트** — 기대값이 구현을 다시 말한다

```csharp
// ❌ 코드와 같은 방식으로 기대값을 계산한다
[Test]
public void Damage_AppliesArmor()
{
    int expected = Mathf.Max(0, 50 - 20 / 2);
    Assert.AreEqual(expected, Combat.Damage(attack: 50, armor: 20));
}

// ✅ 독립된 리터럴 (GDD 의 수치 · 손으로 푼 예시)
[Test]
public void Damage_AppliesArmor()
{
    Assert.AreEqual(40, Combat.Damage(attack: 50, armor: 20));
}
```

## 대역(mock · fake)은 시스템 경계에만

대역을 쓰는 곳:

- 시간 (`Time.deltaTime` · `Time.time` → `ITimeSource` 주입)
- 랜덤 (`Random` → 시드 고정 `IRandom` 주입)
- 입력 (Input System → `IPlayerInput`)
- 파일 · PlayerPrefs · 네트워크 · 플랫폼 SDK (광고 · 결제 · 리더보드)

대역을 쓰지 않는 곳:

- 내가 만든 클래스 · 모듈
- 내부 협력 객체
- 내가 통제하는 모든 것

### 대역을 끼우기 쉬운 설계

**1. 의존성을 주입받는다**

```csharp
// ✅ 대역을 끼우기 쉽다
public sealed class StaminaModel
{
    private readonly ITimeSource _time;
    public StaminaModel(ITimeSource time) => _time = time;
}

// ❌ 끼우기 어렵다 — 엔진 static 에 직접 묶임
public sealed class StaminaModel
{
    public void Tick() => _value += _regen * Time.deltaTime;
}
```

**2. 범용 통로 대신 작업별 인터페이스**

```csharp
// ✅ 작업마다 메서드 — 대역이 한 가지 모양만 돌려준다
public interface ILeaderboard
{
    Task SubmitScore(int score);
    Task<IReadOnlyList<Entry>> GetTop(int count);
}

// ❌ 범용 통로 — 대역 안에 분기 로직이 필요해진다
public interface IPlatformService
{
    Task<object> Call(string endpoint, object payload);
}
```

작업별 인터페이스면 대역이 한 모양만 돌려주고, 테스트 준비에 분기가 없고, 테스트가 어떤 작업을 쓰는지 바로 보인다.
