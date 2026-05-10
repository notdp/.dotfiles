#!/usr/bin/env bash
# notify-tmux-title.sh - say the current tmux window title and a stable pane
# name so the audio cue maps to a visible pane label.
#
# Behaviour
#   1. Read --app (cc|droid) and --event (stop|notification) from argv.
#   2. If TMUX_PANE exists, assign/read stable names for panes in the same
#      window and keep them visible via pane-border-status.
#   3. If tmux window title is non-empty: `say <window title> <pane name>`.
#      Otherwise: fall back to the original static app/event sound.
#
# Env overrides
#   NOTIFY_TMUX_TITLE_SOUND_<APP>_<EVENT>   Force a specific fallback sound
#   NOTIFY_TMUX_TITLE_SOUND                 Force a single fallback sound
#   NOTIFY_TMUX_TITLE_PANE_NAMES            Space-separated pane name pool
#   NOTIFY_TMUX_TITLE_RANDOM_SEED           Deterministic random seed for tests
#   NOTIFY_TMUX_TITLE_DRY_RUN=1             Print actions instead of executing
#
# Exit codes
#   0  ok
#   2  unsupported app/event combination

set -u

APP=""
EVENT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app)
      APP="${2:-}"
      shift 2
      ;;
    --event)
      EVENT="${2:-}"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

# Validate app/event up front so misconfigured hooks fail loudly.
case "$APP:$EVENT" in
  droid:stop|droid:notification|cc:stop|cc:notification) ;;
  *)
    echo "unsupported app/event: $APP/$EVENT" >&2
    exit 2
    ;;
esac

# --- Pick fallback sound -----------------------------------------------------
sound_for() {
  local app_key event_key specific_var specific_sound
  app_key="$(printf '%s' "$APP" | tr '[:lower:]-' '[:upper:]_')"
  event_key="$(printf '%s' "$EVENT" | tr '[:lower:]-' '[:upper:]_')"
  specific_var="NOTIFY_TMUX_TITLE_SOUND_${app_key}_${event_key}"
  specific_sound="$(printenv "$specific_var" 2>/dev/null || true)"

  if [[ -n "$specific_sound" ]]; then
    echo "$specific_sound"
    return 0
  fi
  if [[ -n "${NOTIFY_TMUX_TITLE_SOUND:-}" ]]; then
    echo "$NOTIFY_TMUX_TITLE_SOUND"
    return 0
  fi

  case "$APP:$EVENT" in
    droid:stop) echo "${HOME}/.factory/sounds/fx-ok01.wav" ;;
    droid:notification) echo "${HOME}/.factory/sounds/fx-ack01.wav" ;;
    cc:stop) echo "/System/Library/Sounds/Ping.aiff" ;;
    cc:notification) echo "/System/Library/Sounds/Funk.aiff" ;;
  esac
}

FALLBACK_SOUND="$(sound_for)"

DEFAULT_PANE_NAMES=(
  "及时雨宋江" "玉麒麟卢俊义" "智多星吴用" "入云龙公孙胜"
  "大刀关胜" "豹子头林冲" "霹雳火秦明" "双鞭呼延灼"
  "小李广花荣" "小旋风柴进" "扑天雕李应" "美髯公朱仝"
  "花和尚鲁智深" "行者武松" "双枪将董平" "没羽箭张清"
  "青面兽杨志" "金枪手徐宁" "急先锋索超" "神行太保戴宗"
  "赤发鬼刘唐" "黑旋风李逵" "九纹龙史进" "没遮拦穆弘"
  "插翅虎雷横" "混江龙李俊" "立地太岁阮小二" "船火儿张横"
  "短命二郎阮小五" "浪里白条张顺" "活阎罗阮小七" "病关索杨雄"
  "拼命三郎石秀" "两头蛇解珍" "双尾蝎解宝" "浪子燕青"
  "神机军师朱武" "镇三山黄信" "病尉迟孙立" "丑郡马宣赞"
  "井木犴郝思文" "百胜将韩滔" "天目将彭玘" "圣水将单廷珪"
  "神火将魏定国" "圣手书生萧让" "铁面孔目裴宣" "摩云金翅欧鹏"
  "火眼狻猊邓飞" "锦毛虎燕顺" "锦豹子杨林" "轰天雷凌振"
  "神算子蒋敬" "小温侯吕方" "赛仁贵郭盛" "神医安道全"
  "紫髯伯皇甫端" "矮脚虎王英" "一丈青扈三娘" "丧门神鲍旭"
  "混世魔王樊瑞" "毛头星孔明" "独火星孔亮" "八臂哪吒项充"
  "飞天大圣李衮" "玉臂匠金大坚" "铁笛仙马麟" "出洞蛟童威"
  "翻江蜃童猛" "玉幡竿孟康" "通臂猿侯健" "跳涧虎陈达"
  "白花蛇杨春" "白面郎君郑天寿" "九尾龟陶宗旺" "铁扇子宋清"
  "铁叫子乐和" "花项虎龚旺" "中箭虎丁得孙" "小遮拦穆春"
  "操刀鬼曹正" "云里金刚宋万" "摸着天杜迁" "病大虫薛永"
  "金眼彪施恩" "打虎将李忠" "小霸王周通" "金钱豹子汤隆"
  "鬼脸儿杜兴" "出林龙邹渊" "独角龙邹润" "旱地忽律朱贵"
  "笑面虎朱富" "铁臂膊蔡福" "一枝花蔡庆" "催命判官李立"
  "青眼虎李云" "没面目焦挺" "石将军石勇" "小尉迟孙新"
  "母大虫顾大嫂" "菜园子张青" "母夜叉孙二娘" "活闪婆王定六"
  "险道神郁保四" "白日鼠白胜" "鼓上蚤时迁" "金毛犬段景住"
)

pane_name_pool() {
  if [[ -n "${NOTIFY_TMUX_TITLE_PANE_NAMES:-}" ]]; then
    local custom_names
    read -r -a custom_names <<< "$NOTIFY_TMUX_TITLE_PANE_NAMES"
    printf '%s\n' "${custom_names[@]}"
  else
    printf '%s\n' "${DEFAULT_PANE_NAMES[@]}"
  fi
}

pane_name_for() {
  local target="$1"
  local index="${2:-0}"
  local names
  names="$(pane_name_pool)"
  python3 - "$target" "$index" "$names" <<'PY' 2>/dev/null || true
import os, random, sys, zlib
target, index_raw, names_raw = sys.argv[1], sys.argv[2], sys.argv[3]
names = list(dict.fromkeys(name for name in names_raw.splitlines() if name))
if names:
    seed = os.environ.get("NOTIFY_TMUX_TITLE_RANDOM_SEED")
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    rng.shuffle(names)
    try:
        index = int(index_raw)
    except ValueError:
        index = zlib.crc32(target.encode("utf-8"))
    else:
        index = max(index - 1, 0)
    print(names[index % len(names)])
PY
}

pane_name_assignments() {
  local panes="$1"
  local names
  names="$(pane_name_pool)"
  python3 - "$names" "$panes" <<'PY' 2>/dev/null || true
import os, random, sys
names_raw, panes_raw = sys.argv[1], sys.argv[2]
names = list(dict.fromkeys(name for name in names_raw.splitlines() if name))
if not names:
    raise SystemExit
seed = os.environ.get("NOTIFY_TMUX_TITLE_RANDOM_SEED")
rng = random.Random(seed) if seed is not None else random.SystemRandom()
random_names = names[:]
rng.shuffle(random_names)

rows = []
for raw in panes_raw.splitlines():
    parts = raw.split("\t", 2)
    if len(parts) == 3 and parts[0]:
        rows.append((parts[0], parts[1], parts[2]))

used = set()
needs_name = []
for pane, index, current in rows:
    if current and current not in used:
        used.add(current)
        print(f"{pane}\t{current}\t0")
    else:
        needs_name.append((pane, index))

available = [name for name in random_names if name not in used]
for offset, (pane, _index) in enumerate(needs_name):
    if available:
        name = available.pop(0)
    else:
        name = random_names[offset % len(random_names)]
    used.add(name)
    print(f"{pane}\t{name}\t1")
PY
}

pane_option_name() {
  local target="$1"
  tmux show-option -pvt "$target" @notify_tmux_title_pane_name 2>/dev/null || true
}

ensure_pane_names() {
  local target="${TMUX_PANE:-}"
  [[ -z "$target" ]] && return 0

  if [[ "${NOTIFY_TMUX_TITLE_DRY_RUN:-}" == "1" ]]; then
    local pane_name
    pane_name="$(pane_name_for "$target" 0)"
    printf 'pane-name:%s:%s\n' "$target" "$pane_name"
    PANE_NAME="$pane_name"
    return 0
  fi
  command -v tmux >/dev/null 2>&1 || return 0

  local pane index current_name pane_rows
  while IFS=$'\t' read -r pane index; do
    [[ -n "$pane" ]] || continue
    current_name="$(pane_option_name "$pane")"
    pane_rows+="${pane}"$'\t'"${index}"$'\t'"${current_name}"$'\n'
  done < <(tmux list-panes -t "$target" -F '#{pane_id}	#{pane_index}' 2>/dev/null || true)

  local pane_name should_set
  while IFS=$'\t' read -r pane pane_name should_set; do
    [[ -n "$pane" && -n "$pane_name" ]] || continue
    if [[ "$should_set" == "1" ]]; then
      tmux set-option -qpt "$pane" @notify_tmux_title_pane_name "$pane_name" 2>/dev/null || continue
    fi
    tmux select-pane -t "$pane" -T "$pane_name" 2>/dev/null || continue
    [[ "$pane" == "$target" ]] && PANE_NAME="$pane_name"
  done < <(pane_name_assignments "${pane_rows:-}")

  tmux set-option -qwt "$target" pane-border-status top 2>/dev/null || return 0
  tmux set-option -qwt "$target" pane-border-format '#{?pane_active,#[reverse],}#{pane_index} #{@notify_tmux_title_pane_name}' 2>/dev/null || return 0
  [[ -z "$PANE_NAME" ]] && PANE_NAME="$(pane_option_name "$target")"
}

# --- Read tmux title ---------------------------------------------------------
TITLE=""
PANE_NAME=""
if [[ -n "${TMUX_PANE:-}" ]] && command -v tmux >/dev/null 2>&1; then
  TITLE="$(tmux display-message -p -t "$TMUX_PANE" '#W' 2>/dev/null || true)"
fi

# --- Emit --------------------------------------------------------------------
emit_say() {
  if [[ "${NOTIFY_TMUX_TITLE_DRY_RUN:-}" == "1" ]]; then
    printf 'say:%s\n' "$1"
  else
    /usr/bin/say "$1"
  fi
}

emit_sound() {
  [[ -z "$1" ]] && return 0
  if [[ "${NOTIFY_TMUX_TITLE_DRY_RUN:-}" == "1" ]]; then
    printf 'sound:%s\n' "$1"
  else
    /usr/bin/afplay "$1"
  fi
}

ensure_pane_names
if [[ -n "$TITLE" ]]; then
  if [[ -n "$PANE_NAME" ]]; then
    emit_say "$TITLE $PANE_NAME"
  else
    emit_say "$TITLE"
  fi
else
  emit_sound "$FALLBACK_SOUND"
fi
