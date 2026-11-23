from http.server import BaseHTTPRequestHandler
import json
import zipfile
import io
import os
import re
import math
import xml.etree.ElementTree as ET

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            req = json.loads(post_data.decode('utf-8'))
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            template_path = os.path.join(base_dir, "Time.xlsx")
            if not os.path.exists(template_path):
                template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Time.xlsx")
            if not os.path.exists(template_path):
                template_path = "Time.xlsx"
            if not os.path.exists(template_path):
                self.send_response(404)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Time.xlsx template not found"}).encode())
                return

            with zipfile.ZipFile(template_path, 'r') as z_in:
                files = {name: z_in.read(name) for name in z_in.namelist()}

            ET.register_namespace('', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')
            ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
            ET.register_namespace('mc', 'http://schemas.openxmlformats.org/markup-compatibility/2006')
            ET.register_namespace('x14ac', 'http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac')
            ET.register_namespace('c', 'http://schemas.openxmlformats.org/drawingml/2006/chart')
            ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')

            tree1 = ET.fromstring(files['xl/worksheets/sheet1.xml'])
            tree2 = ET.fromstring(files['xl/worksheets/sheet2.xml'])
            ns = {'': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

            def set_cell_dom(tree, cell_ref, val, is_str=False, new_formula=None):
                for c in tree.findall('.//c', ns):
                    if c.attrib.get('r') == cell_ref:
                        f_elem = c.find('f', ns)
                        if new_formula is not None:
                            if new_formula:
                                if f_elem is None:
                                    f_elem = ET.Element('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}f')
                                    c.insert(0, f_elem)
                                f_elem.attrib.clear()
                                f_elem.text = new_formula
                            else:
                                if f_elem is not None:
                                    c.remove(f_elem)
                                    f_elem = None
                        
                        # Remove all children except f_elem
                        for child in list(c):
                            if child != f_elem:
                                c.remove(child)
                        
                        val_str = str(val) if val is not None else ''
                        
                        if f_elem is not None:
                            if is_str:
                                c.attrib['t'] = 'str'  # OpenXML standard for string formula result
                            else:
                                c.attrib.pop('t', None)  # Default for numeric formula result is number
                            v_el = ET.SubElement(c, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                            v_el.text = val_str
                        else:
                            if is_str:
                                c.attrib['t'] = 'inlineStr'
                                is_el = ET.SubElement(c, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is')
                                t_el = ET.SubElement(is_el, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                                t_el.text = val_str
                            else:
                                c.attrib.pop('t', None)
                                v_el = ET.SubElement(c, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                                v_el.text = val_str
                        return

            date_val = req.get('date', '')
            process_val = req.get('process', '')
            emp_val = req.get('employee', '')
            model_val = req.get('model', 'RG21')
            steps = req.get('steps', [])

            # Automatically compact runs if columns were skipped (ensure non-empty columns are packed sequentially 1, 2, 3...)
            active_cols = []
            for col_idx in range(10):
                has_val = any(s.get('runs', [])[col_idx] is not None for s in steps if len(s.get('runs', [])) > col_idx)
                if has_val:
                    active_cols.append(col_idx)

            if active_cols and active_cols != list(range(len(active_cols))):
                for s in steps:
                    orig_runs = s.get('runs', [])
                    new_runs = []
                    for col_idx in active_cols:
                        val = orig_runs[col_idx] if col_idx < len(orig_runs) else None
                        new_runs.append(val)
                    while len(new_runs) < 10:
                        new_runs.append(None)
                    s['runs'] = new_runs

            parts = date_val.split('-')
            short_date = f"{parts[2]}/{parts[1]}/{parts[0][2:]}" if len(parts) == 3 else date_val

            if date_val:
                set_cell_dom(tree1, 'B1', date_val, is_str=True)
                set_cell_dom(tree2, 'CB1', f":   {short_date}", is_str=True)
            if process_val:
                set_cell_dom(tree1, 'B2', process_val, is_str=True)
                set_cell_dom(tree2, 'A2', f"PROCESS NAME :   {process_val}", is_str=True)
            if emp_val:
                set_cell_dom(tree1, 'M2', emp_val, is_str=True)
            if model_val:
                set_cell_dom(tree1, 'B3', model_val, is_str=True)
                set_cell_dom(tree2, 'E1', f"MODEL : {model_val}", is_str=True)

            swct_plot_mode = req.get('swctPlotMode', 'min')

            # Calculate round totals to identify best/worst round
            round_sums = [0.0] * 10
            round_counts = [0] * 10
            for s in steps:
                r_list = s.get('runs', [])
                for r_idx, r_val in enumerate(r_list[:10]):
                    if r_val is not None:
                        round_sums[r_idx] += float(r_val)
                        round_counts[r_idx] += 1

            best_r_idx = 0
            worst_r_idx = 0
            min_r_sum = float('inf')
            max_r_sum = float('-inf')
            for r_idx in range(10):
                if round_counts[r_idx] > 0:
                    if round_sums[r_idx] < min_r_sum:
                        min_r_sum = round_sums[r_idx]
                        best_r_idx = r_idx
                    if round_sums[r_idx] > max_r_sum:
                        max_r_sum = round_sums[r_idx]
                        worst_r_idx = r_idx

            col_letters = ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
            pts_ser0 = []
            pts_ser1 = []
            step_plot_vals = []
            cum_time = 0.0

            col_totals = [0.0] * 10
            total_min_sum = 0.0
            total_max_sum = 0.0
            total_avg_sum = 0.0

            for s_idx, s in enumerate(steps):
                time_row = 5 + s_idx
                swct_row = 7 + s_idx * 2
                chart_idx = s_idx * 2
                step_name = s.get('name', '')
                runs = s.get('runs', [])

                if time_row <= 33:
                    set_cell_dom(tree1, f'A{time_row}', s_idx + 1, is_str=False)
                    set_cell_dom(tree1, f'B{time_row}', step_name, is_str=True)
                    for r_idx, r_val in enumerate(runs[:10]):
                        if r_val is not None:
                            r_num = float(r_val)
                            set_cell_dom(tree1, f'{col_letters[r_idx]}{time_row}', f'{r_num:.2f}', is_str=False)
                            col_totals[r_idx] += r_num
                        else:
                            set_cell_dom(tree1, f'{col_letters[r_idx]}{time_row}', '', is_str=True)

                    valid_runs = [float(r) for r in runs if r is not None]
                    if valid_runs:
                        min_val = min(valid_runs)
                        max_val = max(valid_runs)
                        fluc_val = max_val - min_val
                        avg_val = sum(valid_runs) / len(valid_runs)

                        # Determine plot_val and target column for SWCT according to swct_plot_mode
                        target_col = 'M'
                        if swct_plot_mode == 'min':
                            plot_val = min_val
                            target_col = 'M'
                        elif swct_plot_mode == 'max':
                            plot_val = max_val
                            target_col = 'N'
                        elif swct_plot_mode == 'avg':
                            plot_val = avg_val
                            target_col = 'P'
                        elif swct_plot_mode == 'best_round':
                            val_at_best = runs[best_r_idx] if best_r_idx < len(runs) and runs[best_r_idx] is not None else min_val
                            plot_val = float(val_at_best)
                            target_col = col_letters[best_r_idx] if best_r_idx < len(col_letters) else 'M'
                        elif swct_plot_mode == 'worst_round':
                            val_at_worst = runs[worst_r_idx] if worst_r_idx < len(runs) and runs[worst_r_idx] is not None else max_val
                            plot_val = float(val_at_worst)
                            target_col = col_letters[worst_r_idx] if worst_r_idx < len(col_letters) else 'M'
                        elif swct_plot_mode.startswith('round_'):
                            r_num = int(swct_plot_mode.replace('round_', '')) - 1
                            val_at_r = runs[r_num] if 0 <= r_num < len(runs) and runs[r_num] is not None else min_val
                            plot_val = float(val_at_r)
                            target_col = col_letters[r_num] if 0 <= r_num < len(col_letters) else 'M'
                        else:
                            plot_val = min_val
                            target_col = 'M'

                        swct_formula = f"IF('TIME MEASUREMENT'!{target_col}{time_row}=\"\",\"\",'TIME MEASUREMENT'!{target_col}{time_row})"

                        set_cell_dom(tree1, f'M{time_row}', f'{min_val:.2f}', is_str=False, new_formula=f'IF(COUNT(C{time_row}:L{time_row})=0,"",MIN(C{time_row}:L{time_row}))')
                        set_cell_dom(tree1, f'N{time_row}', f'{max_val:.2f}', is_str=False, new_formula=f'IF(COUNT(C{time_row}:L{time_row})=0,"",MAX(C{time_row}:L{time_row}))')
                        set_cell_dom(tree1, f'O{time_row}', f'{fluc_val:.2f}', is_str=False, new_formula=f'IF(N{time_row}="","",N{time_row}-M{time_row})')
                        set_cell_dom(tree1, f'P{time_row}', f'{avg_val:.2f}', is_str=False, new_formula=f'IF(COUNT(C{time_row}:L{time_row})=0,"",AVERAGE(C{time_row}:L{time_row}))')

                        total_min_sum += min_val
                        total_max_sum += max_val
                        total_avg_sum += avg_val

                        # SWCT Step Name retains formula =IF('TIME MEASUREMENT'!B{time_row}="","",'TIME MEASUREMENT'!B{time_row})
                        # and safely stores string result in <v> with t="str"
                        set_cell_dom(tree2, f'C{swct_row}', step_name, is_str=True)
                        set_cell_dom(tree2, f'G{swct_row}', f'{plot_val:.2f}', is_str=False, new_formula=swct_formula)

                        pts_ser0.append((chart_idx, cum_time))
                        pts_ser1.append((chart_idx, plot_val))
                        step_plot_vals.append(plot_val)

                        set_cell_dom(tree2, f'EE{swct_row}', f'{cum_time:.2f}', is_str=False)
                        cum_time += plot_val
                    else:
                        set_cell_dom(tree1, f'M{time_row}', '', is_str=True, new_formula=f'IF(COUNT(C{time_row}:L{time_row})=0,"",MIN(C{time_row}:L{time_row}))')
                        set_cell_dom(tree1, f'N{time_row}', '', is_str=True, new_formula=f'IF(COUNT(C{time_row}:L{time_row})=0,"",MAX(C{time_row}:L{time_row}))')
                        set_cell_dom(tree1, f'O{time_row}', '', is_str=True, new_formula=f'IF(N{time_row}="","",N{time_row}-M{time_row})')
                        set_cell_dom(tree1, f'P{time_row}', '', is_str=True, new_formula=f'IF(COUNT(C{time_row}:L{time_row})=0,"",AVERAGE(C{time_row}:L{time_row}))')

                        set_cell_dom(tree2, f'C{swct_row}', step_name, is_str=True)
                        set_cell_dom(tree2, f'G{swct_row}', '', is_str=True, new_formula=f"IF('TIME MEASUREMENT'!M{time_row}=\"\",\"\",'TIME MEASUREMENT'!M{time_row})")
                        set_cell_dom(tree2, f'EE{swct_row}', f'{cum_time:.2f}', is_str=False)

                        pts_ser0.append((chart_idx, cum_time))
                        pts_ser1.append((chart_idx, 0.0))
                        step_plot_vals.append(0.0)

            # Clear all unused step rows so they never display 0.00
            for u_row in range(5 + len(steps), 34):
                set_cell_dom(tree1, f'A{u_row}', '', is_str=True)
                set_cell_dom(tree1, f'B{u_row}', '', is_str=True)
                for col_letter in col_letters:
                    set_cell_dom(tree1, f'{col_letter}{u_row}', '', is_str=True)
                set_cell_dom(tree1, f'M{u_row}', '', is_str=True, new_formula=f'IF(COUNT(C{u_row}:L{u_row})=0,"",MIN(C{u_row}:L{u_row}))')
                set_cell_dom(tree1, f'N{u_row}', '', is_str=True, new_formula=f'IF(COUNT(C{u_row}:L{u_row})=0,"",MAX(C{u_row}:L{u_row}))')
                set_cell_dom(tree1, f'O{u_row}', '', is_str=True, new_formula=f'IF(N{u_row}="","",N{u_row}-M{u_row})')
                set_cell_dom(tree1, f'P{u_row}', '', is_str=True, new_formula=f'IF(COUNT(C{u_row}:L{u_row})=0,"",AVERAGE(C{u_row}:L{u_row}))')

            # Clear unused rows in Sheet 2 (SWCT)
            for u_s_idx in range(len(steps), 26):
                u_swct_row = 7 + u_s_idx * 2
                set_cell_dom(tree2, f'A{u_swct_row}', '', is_str=True)
                set_cell_dom(tree2, f'C{u_swct_row}', '', is_str=True)
                set_cell_dom(tree2, f'G{u_swct_row}', '', is_str=True)
                set_cell_dom(tree2, f'EE{u_swct_row}', '', is_str=True)

            # Sheet 1 row 34 TOTAL
            active_col_totals = [tot for tot in col_totals if tot > 0]
            for r_idx in range(10):
                col_c = col_letters[r_idx]
                if col_totals[r_idx] > 0:
                    set_cell_dom(tree1, f'{col_c}34', f'{col_totals[r_idx]:.2f}', is_str=False, new_formula=f'IF(COUNT({col_c}5:{col_c}33)=0,"",SUM({col_c}5:{col_c}33))')
                else:
                    set_cell_dom(tree1, f'{col_c}34', '', is_str=True, new_formula=f'IF(COUNT({col_c}5:{col_c}33)=0,"",SUM({col_c}5:{col_c}33))')

            if active_col_totals:
                min_total = min(active_col_totals)
                max_total = max(active_col_totals)
                fluc_total = max_total - min_total
                avg_total = sum(active_col_totals) / len(active_col_totals)
                set_cell_dom(tree1, 'M34', f'{min_total:.2f}', is_str=False, new_formula='IF(COUNT(C34:L34)=0,"",MIN(C34:L34))')
                set_cell_dom(tree1, 'N34', f'{max_total:.2f}', is_str=False, new_formula='IF(COUNT(C34:L34)=0,"",MAX(C34:L34))')
                set_cell_dom(tree1, 'O34', f'{fluc_total:.2f}', is_str=False, new_formula='IF(N34="","",N34-M34)')
                set_cell_dom(tree1, 'P34', f'{avg_total:.2f}', is_str=False, new_formula='IF(COUNT(C34:L34)=0,"",AVERAGE(C34:L34))')
            else:
                set_cell_dom(tree1, 'M34', '', is_str=True, new_formula='IF(COUNT(C34:L34)=0,"",MIN(C34:L34))')
                set_cell_dom(tree1, 'N34', '', is_str=True, new_formula='IF(COUNT(C34:L34)=0,"",MAX(C34:L34))')
                set_cell_dom(tree1, 'O34', '', is_str=True, new_formula='IF(N34="","",N34-M34)')
                set_cell_dom(tree1, 'P34', '', is_str=True, new_formula='IF(COUNT(C34:L34)=0,"",AVERAGE(C34:L34))')

            total_swct = cum_time
            set_cell_dom(tree2, 'BD2', f'{total_swct:.2f}', is_str=False)
            set_cell_dom(tree2, 'G58', f'{total_swct:.2f}', is_str=False)
            set_cell_dom(tree2, 'G60', f'{total_swct:.2f}', is_str=False)

            mode_labels = {
                'min': 'Min Time',
                'avg': 'Average',
                'max': 'Max Time',
                'best_round': 'Best Round',
                'worst_round': 'Worst Round'
            }
            label = mode_labels.get(swct_plot_mode, swct_plot_mode)
            set_cell_dom(tree2, 'AT2', f'CYCLE TIME ({label})', is_str=True)

            # Inject precomputed points into chart1.xml
            chart_xml = files['xl/charts/chart1.xml'].decode('utf-8')

            def build_num_cache(pts, format_code="0.00", total_count=50):
                lines = [f'<c:numCache><c:formatCode>{format_code}</c:formatCode><c:ptCount val="{total_count}"/>']
                pt_map = {idx: val for idx, val in pts}
                for i in range(total_count):
                    if i in pt_map:
                        val = pt_map[i]
                        lines.append(f'<c:pt idx="{i}"><c:v>{val:.2f}</c:v></c:pt>')
                    elif i % 2 == 0:
                        lines.append(f'<c:pt idx="{i}"><c:v>0</c:v></c:pt>')
                lines.append('</c:numCache>')
                return "".join(lines)

            cache0 = build_num_cache(pts_ser0)
            cache1 = build_num_cache(pts_ser1)

            chart_xml = re.sub(
                r'(<c:f>SWCT!\$EE\$7:\$EE\$56</c:f>)(?:<c:numCache>.*?</c:numCache>)?',
                r'\g<1>' + cache0,
                chart_xml,
                flags=re.DOTALL
            )

            chart_xml = re.sub(
                r'(<c:f>SWCT!\$G\$7:\$G\$56</c:f>)(?:<c:numCache>.*?</c:numCache>)?',
                r'\g<1>' + cache1,
                chart_xml,
                flags=re.DOTALL
            )

            # Dynamic chart axis scaling based on total_swct time
            buffer = max(15.0, total_swct * 0.12)
            raw_max = total_swct + buffer
            step = 10
            if raw_max > 200: step = 20
            if raw_max > 500: step = 50
            if raw_max > 1000: step = 100
            max_axis = max(60, int(math.ceil(raw_max / step) * step))

            major_unit = 5
            if max_axis > 180: major_unit = 10
            if max_axis > 400: major_unit = 20
            if max_axis > 1000: major_unit = 50

            chart_xml = re.sub(
                r'(<(?:c:)?valAx>[\s\S]*?<(?:c:)?scaling>[\s\S]*?<(?:c:)?max val=")\d+("\s*/>)',
                r'\g<1>' + str(max_axis) + r'\g<2>',
                chart_xml
            )
            chart_xml = re.sub(
                r'(<(?:c:)?valAx>[\s\S]*?<(?:c:)?majorUnit val=")\d+("\s*/>)',
                r'\g<1>' + str(major_unit) + r'\g<2>',
                chart_xml
            )

            # Populate Sheet 3: Raw Data Log
            raw_cycles = req.get('rawCycles', [])
            if raw_cycles:
                cols_xml = '<cols><col width="8" customWidth="1" min="1" max="1" /><col width="18" customWidth="1" min="2" max="2" /><col width="25" customWidth="1" min="3" max="3" /><col width="18" customWidth="1" min="4" max="4" /><col width="18" customWidth="1" min="5" max="5" /><col width="18" customWidth="1" min="6" max="6" /><col width="30" customWidth="1" min="7" max="7" /></cols>'
                raw_rows = []
                raw_rows.append('<row r="1"><c r="A1" t="inlineStr"><is><t>No.</t></is></c><c r="B1" t="inlineStr"><is><t>Employee</t></is></c><c r="C1" t="inlineStr"><is><t>Work Step</t></is></c><c r="D1" t="inlineStr"><is><t>Start Time (sec)</t></is></c><c r="E1" t="inlineStr"><is><t>End Time (sec)</t></is></c><c r="F1" t="inlineStr"><is><t>Cycle Time (sec)</t></is></c><c r="G1" t="inlineStr"><is><t>Note</t></is></c></row>')
                
                def esc_s(s):
                    if s is None: return ''
                    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')

                for idx, c in enumerate(raw_cycles):
                    r = idx + 2
                    no = idx + 1
                    e_emp = esc_s(c.get('employee', emp_val))
                    e_step = esc_s(c.get('step', ''))
                    e_start = f"{float(c.get('start', 0)):.2f}"
                    e_end = f"{float(c.get('end', 0)):.2f}"
                    e_dur = f"{float(c.get('duration', 0)):.2f}"
                    c_round = c.get('cycleRound', '')
                    round_tag = f"รอบที่ {c_round}" if c_round else ""
                    c_note = c.get('note', '')
                    if round_tag and round_tag not in c_note:
                        full_note = f"{round_tag} {c_note}".strip()
                    else:
                        full_note = c_note or round_tag
                    e_note = esc_s(full_note)
                    
                    raw_rows.append(
                        f'<row r="{r}">'
                        f'<c r="A{r}"><v>{no}</v></c>'
                        f'<c r="B{r}" t="inlineStr"><is><t>{e_emp}</t></is></c>'
                        f'<c r="C{r}" t="inlineStr"><is><t>{e_step}</t></is></c>'
                        f'<c r="D{r}"><v>{e_start}</v></c>'
                        f'<c r="E{r}"><v>{e_end}</v></c>'
                        f'<c r="F{r}"><v>{e_dur}</v></c>'
                        f'<c r="G{r}" t="inlineStr"><is><t>{e_note}</t></is></c>'
                        f'</row>'
                    )

                dim_ref = f"A1:G{max(1, len(raw_cycles) + 1)}"
                sheet3_xml = (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                    '<sheetPr><outlinePr summaryBelow="1" summaryRight="1" /><pageSetUpPr /></sheetPr>'
                    f'<dimension ref="{dim_ref}" />'
                    '<sheetViews><sheetView workbookViewId="0"><selection activeCell="A1" sqref="A1" /></sheetView></sheetViews>'
                    '<sheetFormatPr baseColWidth="8" defaultRowHeight="15" />'
                    f'{cols_xml}'
                    f'<sheetData>{"".join(raw_rows)}</sheetData>'
                    '<pageMargins left="0.75" right="0.75" top="1" bottom="1" header="0.5" footer="0.5" />'
                    '</worksheet>'
                )
                files['xl/worksheets/sheet3.xml'] = sheet3_xml.encode('utf-8')

            # Populate Sheet 4: YAMA (YAMAZUMI CHART)
            if 'xl/worksheets/sheet4.xml' in files:
                tree4 = ET.fromstring(files['xl/worksheets/sheet4.xml'])
                set_cell_dom(tree4, 'J2', process_val, is_str=True)
                set_cell_dom(tree4, 'P2', emp_val, is_str=True)
                set_cell_dom(tree4, 'V2', date_val, is_str=True)
                set_cell_dom(tree4, 'H2', model_val, is_str=True)

                for s_idx, s in enumerate(steps):
                    y_row = 5 + s_idx
                    swct_row = 7 + s_idx * 2
                    if y_row <= 21:
                        set_cell_dom(tree4, f'B{y_row}', s_idx + 1, is_str=False)
                        step_name = s.get('name', '')
                        plot_val = step_plot_vals[s_idx] if s_idx < len(step_plot_vals) else 0.0
                        set_cell_dom(tree4, f'C{y_row}', step_name, is_str=True, new_formula=f'IF(SWCT!C{swct_row}="","",SWCT!C{swct_row})')
                        set_cell_dom(tree4, f'H{y_row}', f'{plot_val:.2f}', is_str=False, new_formula=f'IF(SWCT!G{swct_row}="","",SWCT!G{swct_row})')

                for u_row in range(5 + len(steps), 22):
                    set_cell_dom(tree4, f'B{u_row}', '', is_str=True)
                    set_cell_dom(tree4, f'C{u_row}', '', is_str=True)
                    set_cell_dom(tree4, f'H{u_row}', '', is_str=True)

                if active_col_totals:
                    set_cell_dom(tree4, 'H22', f'{min_total:.2f}', is_str=False, new_formula="IF('TIME MEASUREMENT'!M34=\"\",\"\",'TIME MEASUREMENT'!M34)")
                    set_cell_dom(tree4, 'H23', f'{max_total:.2f}', is_str=False, new_formula="IF('TIME MEASUREMENT'!N34=\"\",\"\",'TIME MEASUREMENT'!N34)")
                    set_cell_dom(tree4, 'H24', f'{fluc_total:.2f}', is_str=False, new_formula="IF('TIME MEASUREMENT'!O34=\"\",\"\",'TIME MEASUREMENT'!O34)")
                    set_cell_dom(tree4, 'H25', f'{avg_total:.2f}', is_str=False, new_formula="IF('TIME MEASUREMENT'!P34=\"\",\"\",'TIME MEASUREMENT'!P34)")
                else:
                    set_cell_dom(tree4, 'H22', '', is_str=True, new_formula="IF('TIME MEASUREMENT'!M34=\"\",\"\",'TIME MEASUREMENT'!M34)")
                    set_cell_dom(tree4, 'H23', '', is_str=True, new_formula="IF('TIME MEASUREMENT'!N34=\"\",\"\",'TIME MEASUREMENT'!N34)")
                    set_cell_dom(tree4, 'H24', '', is_str=True, new_formula="IF('TIME MEASUREMENT'!O34=\"\",\"\",'TIME MEASUREMENT'!O34)")
                    set_cell_dom(tree4, 'H25', '', is_str=True, new_formula="IF('TIME MEASUREMENT'!P34=\"\",\"\",'TIME MEASUREMENT'!P34)")

                files['xl/worksheets/sheet4.xml'] = ET.tostring(tree4, encoding='utf-8', xml_declaration=True)

            # Update chart2.xml (YAMAZUMI Stacked Column Chart)
            if 'xl/charts/chart2.xml' in files:
                tree_c2 = ET.fromstring(files['xl/charts/chart2.xml'])
                c_ns = {'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart'}

                for ser in tree_c2.findall('.//c:ser', c_ns):
                    f_el = ser.find('.//c:val//c:f', c_ns)
                    if f_el is not None and 'YAMA!$H$' in (f_el.text or ''):
                        m = re.search(r'\$H\$(\d+)', f_el.text)
                        if m:
                            row_num = int(m.group(1))
                            s_idx = row_num - 5
                            val_el = ser.find('.//c:val', c_ns)
                            if val_el is not None:
                                num_ref = val_el.find('c:numRef', c_ns)
                                target_parent = num_ref if num_ref is not None else val_el
                                nc = target_parent.find('c:numCache', c_ns)
                                if nc is not None:
                                    target_parent.remove(nc)

                                new_nc = ET.SubElement(target_parent, '{http://schemas.openxmlformats.org/drawingml/2006/chart}numCache')
                                if 0 <= s_idx < len(step_plot_vals):
                                    fc = ET.SubElement(new_nc, '{http://schemas.openxmlformats.org/drawingml/2006/chart}formatCode')
                                    fc.text = '0.00'
                                    pc = ET.SubElement(new_nc, '{http://schemas.openxmlformats.org/drawingml/2006/chart}ptCount')
                                    pc.attrib['val'] = '2'
                                    pt0 = ET.SubElement(new_nc, '{http://schemas.openxmlformats.org/drawingml/2006/chart}pt')
                                    pt0.attrib['idx'] = '0'
                                    v0 = ET.SubElement(pt0, '{http://schemas.openxmlformats.org/drawingml/2006/chart}v')
                                    v0.text = f'{step_plot_vals[s_idx]:.2f}'
                                else:
                                    fc = ET.SubElement(new_nc, '{http://schemas.openxmlformats.org/drawingml/2006/chart}formatCode')
                                    fc.text = 'General'
                                    pc = ET.SubElement(new_nc, '{http://schemas.openxmlformats.org/drawingml/2006/chart}ptCount')
                                    pc.attrib['val'] = '2'
                                    pt0 = ET.SubElement(new_nc, '{http://schemas.openxmlformats.org/drawingml/2006/chart}pt')
                                    pt0.attrib['idx'] = '0'
                                    v0 = ET.SubElement(pt0, '{http://schemas.openxmlformats.org/drawingml/2006/chart}v')
                                    v0.text = '0'

                    cat_v = ser.find('.//c:cat//c:v', c_ns)
                    if cat_v is not None:
                        cat_v.text = f'{emp_val} ({process_val})'

                # Dynamic axis scaling for chart2
                val_ax2 = tree_c2.find('.//c:valAx', c_ns)
                if val_ax2 is not None:
                    max_el2 = val_ax2.find('.//c:scaling/c:max', c_ns)
                    target_max2 = max(30.0, total_swct * 1.15)
                    unit2 = 5 if target_max2 <= 60 else (10 if target_max2 <= 180 else 20)
                    max_val2 = int(math.ceil(target_max2 / unit2) * unit2)
                    if max_el2 is not None:
                        max_el2.attrib['val'] = str(max_val2)
                    maj_el2 = val_ax2.find('c:majorUnit', c_ns)
                    if maj_el2 is not None:
                        maj_el2.attrib['val'] = str(unit2)

                files['xl/charts/chart2.xml'] = ET.tostring(tree_c2, encoding='utf-8')

            # Clean calcChain to ensure Excel opens without recovery alert
            files.pop('xl/calcChain.xml', None)
            if '[Content_Types].xml' in files:
                ct_clean = files['[Content_Types].xml'].decode('utf-8')
                ct_clean = re.sub(r'<Override[^>]*PartName="/xl/calcChain\.xml"[^>]*/>', '', ct_clean)
                files['[Content_Types].xml'] = ct_clean.encode('utf-8')
            if 'xl/_rels/workbook.xml.rels' in files:
                rels_clean = files['xl/_rels/workbook.xml.rels'].decode('utf-8')
                rels_clean = re.sub(r'<Relationship[^>]*Target="calcChain\.xml"[^>]*/>', '', rels_clean)
                files['xl/_rels/workbook.xml.rels'] = rels_clean.encode('utf-8')

            wb_xml = files['xl/workbook.xml'].decode('utf-8')
            if 'fullCalcOnLoad' not in wb_xml:
                wb_xml = re.sub(r'<calcPr\b[^>]*?/>', r'<calcPr calcId="191029" fullCalcOnLoad="1"/>', wb_xml)

            files['xl/worksheets/sheet1.xml'] = ET.tostring(tree1, encoding='utf-8', xml_declaration=True)
            files['xl/worksheets/sheet2.xml'] = ET.tostring(tree2, encoding='utf-8', xml_declaration=True)
            files['xl/charts/chart1.xml'] = chart_xml.encode('utf-8')
            files['xl/workbook.xml'] = wb_xml.encode('utf-8')

            out_buf = io.BytesIO()
            with zipfile.ZipFile(out_buf, 'w', zipfile.ZIP_DEFLATED) as z_out:
                for name, content in files.items():
                    z_out.writestr(name, content)

            excel_bytes = out_buf.getvalue()

            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.send_header('Content-Length', str(len(excel_bytes)))
            self.end_headers()
            self.wfile.write(excel_bytes)
            print(f"📊 ส่งออกไฟล์ Excel สำเร็จตามแม่แบบ Time.xlsx 100% พร้อมกราฟ SWCT!")
            return
        except Exception as e:
            print(f"❌ Error Exporting Excel: {e}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

