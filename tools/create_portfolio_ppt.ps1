param(
    [string]$OutputPath = "C:\SR\final_project\docs\취업준비\해담-SOAR-포트폴리오-초안.pptx"
)

$ppLayoutBlank = 12
$ppSaveAsOpenXMLPresentation = 24
$ppShapeRectangle = 1
$ppShapeRoundedRectangle = 5
$ppAlignCenter = 2
$msoFalse = 0
$msoTrue = -1

Add-Type -AssemblyName System.Drawing
$navy = [System.Drawing.ColorTranslator]::ToOle('#071827')
$navy2 = [System.Drawing.ColorTranslator]::ToOle('#0D2940')
$cyan = [System.Drawing.ColorTranslator]::ToOle('#2DD4BF')
$sky = [System.Drawing.ColorTranslator]::ToOle('#8BE7FF')
$white = [System.Drawing.ColorTranslator]::ToOle('#F4F8FB')
$muted = [System.Drawing.ColorTranslator]::ToOle('#A9C0D0')
$line = [System.Drawing.ColorTranslator]::ToOle('#28506B')
$orange = [System.Drawing.ColorTranslator]::ToOle('#FFB86B')
$gray = [System.Drawing.ColorTranslator]::ToOle('#D9E5EC')
$font = 'Malgun Gothic'

function Add-Rect($slide, $x, $y, $w, $h, $color, $radius = $false) {
    $type = if ($radius) { $ppShapeRoundedRectangle } else { $ppShapeRectangle }
    $shape = $slide.Shapes.AddShape($type, $x, $y, $w, $h)
    $shape.Fill.ForeColor.RGB = $color
    $shape.Line.Visible = $msoFalse
    return $shape
}

function Add-Text($slide, $text, $x, $y, $w, $h, $size = 20, $color = $white, $bold = $false, $align = 1) {
    if ($x -isnot [int] -and $x -isnot [double]) { throw "Add-Text 좌표 오류: text=$text x=$x y=$y" }
    $box = $slide.Shapes.AddTextbox(1, $x, $y, $w, $h)
    $box.TextFrame.TextRange.Text = $text
    $box.TextFrame.TextRange.Font.NameFarEast = $font
    $box.TextFrame.TextRange.Font.Name = $font
    $box.TextFrame.TextRange.Font.Size = $size
    $box.TextFrame.TextRange.Font.Bold = if ($bold) { $msoTrue } else { $msoFalse }
    $box.TextFrame.TextRange.Font.Color.RGB = $color
    $box.TextFrame.TextRange.ParagraphFormat.Alignment = $align
    $box.TextFrame.MarginLeft = 0; $box.TextFrame.MarginRight = 0
    $box.TextFrame.MarginTop = 0; $box.TextFrame.MarginBottom = 0
    return $box
}

function Add-Header($slide, $section, $title, $num) {
    Add-Text $slide $section 72 44 300 24 13 $cyan $true | Out-Null
    Add-Text $slide $title 72 82 1050 60 34 $white $true | Out-Null
    Add-Text $slide $num 1130 48 70 24 12 $muted $false 3 | Out-Null
    Add-Rect $slide 72 154 1136 2 $line | Out-Null
}

function Add-Placeholder($slide, $label, $x, $y, $w, $h) {
    $card = Add-Rect $slide $x $y $w $h $navy2 $true
    $card.Line.Visible = $msoTrue; $card.Line.ForeColor.RGB = $line
    Add-Text $slide $label $x ($y + $h/2 - 12) $w 24 15 $muted $false 2 | Out-Null
}

$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $directory | Out-Null
if (Test-Path $OutputPath) { Remove-Item -LiteralPath $OutputPath -Force }

$powerpoint = New-Object -ComObject PowerPoint.Application
$powerpoint.Visible = $msoTrue
$presentation = $powerpoint.Presentations.Add($msoTrue)
$presentation.PageSetup.SlideSize = 15 # 16:9

try {
    # 1 Cover
    $s = $presentation.Slides.Add(1, $ppLayoutBlank); $s.Background.Fill.ForeColor.RGB = $navy
    Add-Rect $s 72 72 9 506 $cyan | Out-Null
    Add-Text $s 'HAEDAM SOAR' 112 112 700 28 16 $cyan $true | Out-Null
    Add-Text $s "민원 포털 보안 관제와`n자동 대응 실습" 112 160 900 150 48 $white $true | Out-Null
    Add-Text $s 'Graylog · n8n · pfSense · Wazuh · Ticket Store' 114 334 720 30 20 $muted $false | Out-Null
    Add-Text $s '이름  [                         ]' 112 518 430 28 18 $white $false | Out-Null
    Add-Text $s '역할  [                         ]' 112 556 430 28 18 $white $false | Out-Null
    Add-Text $s '2026' 1080 620 120 24 14 $muted $false 3 | Out-Null

    # 2 Problem and goal
    $s = $presentation.Slides.Add(2, $ppLayoutBlank); $s.Background.Fill.ForeColor.RGB = $navy; Add-Header $s '01  PROJECT' '문제와 목표' '02'
    Add-Text $s "민원 포털의 보안 이벤트를 탐지하고,`n티켓으로 남기며, 대응 결과를 확인하는 실습 환경" 72 205 630 100 27 $white $true | Out-Null
    Add-Text $s '핵심 목표' 72 360 180 28 17 $cyan $true | Out-Null
    Add-Text $s "· 실제 포털 요청을 기준으로 탐지`n· 대응 전후의 정상 사용자 영향 확인`n· 티켓과 알림으로 결과를 추적" 72 402 500 130 20 $gray $false | Out-Null
    Add-Placeholder $s '[ 프로젝트 소개 문장 또는 요구사항 삽입 ]' 690 220 470 260
    Add-Text $s '※ 개인 담당 범위와 프로젝트 소개는 확정 후 입력' 690 500 470 24 14 $muted $false 2 | Out-Null

    # 3 architecture
    $s = $presentation.Slides.Add(3, $ppLayoutBlank); $s.Background.Fill.ForeColor.RGB = $navy; Add-Header $s '02  ARCHITECTURE' '보안 관제 구성' '03'
    $labels = @('민원 포털',"로그 수집`nGraylog","자동화`nn8n",'티켓 저장소','Discord 알림')
    $xs = @(72,300,528,756,984)
    for($i=0; $i -lt $labels.Count; $i++) {
        Add-Rect $s $xs[$i] 285 170 100 $navy2 $true | Out-Null
        Add-Text $s $labels[$i] $xs[$i] 315 170 42 18 $white $true 2 | Out-Null
        if($i -lt 4) { Add-Text $s '→' ($xs[$i]+181) 316 35 30 24 $cyan $true 2 | Out-Null }
    }
    Add-Text $s 'pfSense는 경계 차단, Wazuh는 파일 무결성 감시를 담당한다.' 72 456 920 32 20 $gray $false | Out-Null
    Add-Placeholder $s '[ 구성도 캡처 삽입 ]' 72 520 1136 100

    # 4 response flow
    $s = $presentation.Slides.Add(4, $ppLayoutBlank); $s.Background.Fill.ForeColor.RGB = $navy; Add-Header $s '03  RESPONSE FLOW' '탐지부터 원복까지' '04'
    $steps = @('입력','로그 수집','탐지','자동 대응','효과 확인','원복')
    for($i=0; $i -lt $steps.Count; $i++) {
        $x = 72 + $i*188
        Add-Text $s ('0' + ($i+1)) $x 232 40 22 13 $cyan $true | Out-Null
        Add-Text $s $steps[$i] $x 266 160 34 22 $white $true | Out-Null
        Add-Text $s @('포털 요청','GELF/syslog','Graylog 규칙','n8n 워크플로','차단·정상 비교','담당자 해제')[$i] $x 313 155 50 15 $muted $false | Out-Null
        if($i -lt 5) { Add-Rect $s ($x+154) 286 26 2 $cyan | Out-Null }
    }
    Add-Text $s '검증 원칙: 제어판 UI뿐 아니라 raw 요청과 스크립트 경로로 같은 방어 흐름을 확인' 72 470 1080 34 20 $orange $true | Out-Null

    # 5 cases
    $s = $presentation.Slides.Add(5, $ppLayoutBlank); $s.Background.Fill.ForeColor.RGB = $navy; Add-Header $s '04  CASES' '시나리오와 대응 범위' '05'
    $rows = @(
        @('S1','로그인 무차별 대입','출발지 IP 차단'), @('S8','포털 스캔과 로그인 실패','포털 IP 차단'),
        @('S10','경계 신호·스캔·로그인','pfSense + 포털 차단'), @('H1','민원 도배','민원 작성만 제한'),
        @('H2','타인 민원 반복 조회','계정 잠금 + 포털 IP 차단'), @('H3','처리 결과 조작','권한 회수 + 이력 복원')
    )
    Add-Text $s 'CASE' 82 205 100 22 13 $cyan $true | Out-Null; Add-Text $s '시나리오' 240 205 310 22 13 $cyan $true | Out-Null; Add-Text $s '대응' 680 205 330 22 13 $cyan $true | Out-Null
    for($i=0; $i -lt $rows.Count; $i++) {
        $y=240+$i*56; Add-Rect $s 72 $y 1050 43 $(if($i%2 -eq 0){$navy2}else{$navy}) $false | Out-Null
        Add-Text $s ($rows[$i][0]) 82 ($y+11) 100 20 18 $white $true | Out-Null
        Add-Text $s ($rows[$i][1]) 240 ($y+11) 350 20 17 $gray $false | Out-Null
        Add-Text $s ($rows[$i][2]) 680 ($y+11) 360 20 17 $gray $false | Out-Null
    }
    Add-Text $s 'S4·S7·S12는 연동 준비 후 추가 검증 예정' 72 600 650 24 15 $muted $false | Out-Null

    # 6 H1 case
    $s = $presentation.Slides.Add(6, $ppLayoutBlank); $s.Background.Fill.ForeColor.RGB = $navy; Add-Header $s '05  VALIDATION' 'H1 민원 도배 검증' '06'
    Add-Text $s "한 계정의 짧은 시간 민원 등록을 탐지하고,`n업무 영향이 작은 작성 제한으로 대응" 72 205 600 90 27 $white $true | Out-Null
    Add-Text $s '확인 항목' 72 350 150 24 16 $cyan $true | Out-Null
    Add-Text $s "· 제한된 계정의 작성 요청: 429`n· 로그인·목록 조회: 유지`n· 다른 정상 시민의 작성: 유지`n· 담당자 해제 뒤 작성: 201" 72 390 490 140 19 $gray $false | Out-Null
    Add-Placeholder $s '[ H1 티켓 또는 Discord 캡처 삽입 ]' 690 210 440 235
    Add-Text $s '실측 횟수  [     ]     입력→차단 중앙값  [          ]초' 690 485 460 26 17 $white $false | Out-Null
    Add-Text $s '기준선 오탐  [     ]' 690 527 280 26 17 $white $false | Out-Null

    # 7 evidence
    $s = $presentation.Slides.Add(7, $ppLayoutBlank); $s.Background.Fill.ForeColor.RGB = $navy; Add-Header $s '06  EVIDENCE' '실습 제어판과 독립 검증' '07'
    Add-Text $s "제어판은 실습 순서를 안내하고`n실제 입력은 같은 백엔드 경로로 보낸다." 72 205 560 88 26 $white $true | Out-Null
    Add-Text $s '① raw curl' 72 378 160 24 18 $cyan $true | Out-Null
    Add-Text $s '프로젝트 스크립트 없이 API 직접 요청' 72 412 260 48 16 $gray $false | Out-Null
    Add-Text $s '② CLI' 390 378 160 24 18 $cyan $true | Out-Null
    Add-Text $s '실습 안내의 입력 도구로 재현' 390 412 260 48 16 $gray $false | Out-Null
    Add-Text $s '③ 제어판' 708 378 160 24 18 $cyan $true | Out-Null
    Add-Text $s '같은 입력을 UI에서 순서대로 실행' 708 412 280 48 16 $gray $false | Out-Null
    Add-Placeholder $s '[ 제어판 캡처 삽입 ]' 72 520 1050 90

    # 8 roadmap
    $s = $presentation.Slides.Add(8, $ppLayoutBlank); $s.Background.Fill.ForeColor.RGB = $navy; Add-Header $s '07  ROADMAP' '후속 검증 계획' '08'
    $roadmap = @('H2  타인 민원 엿보기','H3  처리 결과 조작','S4  계정 잠금','S7  홈페이지 변조','S12  요청 폭주')
    for($i=0; $i -lt $roadmap.Count; $i++) {
        $x=72+$i*215; Add-Rect $s $x 270 185 92 $navy2 $true | Out-Null
        Add-Text $s $roadmap[$i] ($x+14) 290 157 38 17 $white $true 2 | Out-Null
        Add-Text $s '[ 준비 ]' ($x+14) 330 157 18 13 $muted $false 2 | Out-Null
    }
    Add-Text $s '다음 작업' 72 445 150 24 16 $cyan $true | Out-Null
    Add-Text $s 'H2 배포·연동 후 기준선, 실측 3회, 티켓 증적을 순서대로 채운다.' 72 484 930 34 21 $white $true | Out-Null
    Add-Text $s '발표 일자  [                         ]     담당 역할  [                         ]' 72 590 900 26 17 $muted $false | Out-Null

    $presentation.SaveAs($OutputPath, $ppSaveAsOpenXMLPresentation)
} finally {
    $presentation.Close()
    $powerpoint.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) | Out-Null
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($powerpoint) | Out-Null
}
