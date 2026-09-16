import pygame
import random
import math
import asyncio

# --- 初期設定 ---
WIDTH, HEIGHT = 1400, 800
FPS = 60

async def main():

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    pygame.mouse.set_visible(False)

    # --- 🎵 オーディオミキサーの初期化とBGM・SEの設定 ---
    pygame.mixer.init()

    # 音量設定の固定値
    BGM_VOLUME = 0.8
    SE_VOLUME = 1.0

    # 1. スタート画面のBGM
    try:
        pygame.mixer.music.load("帝国の侵略.oog") 
        pygame.mixer.music.play(-1) # 初期状態ではスタート画面の曲を無限ループ
        pygame.mixer.music.set_volume(BGM_VOLUME)  # 🌟BGM音量を 0.8 に設定
    except pygame.error:
        print("スタート画面のBGMファイルが見つからないか、読み込めませんでした。そのまま続行します。")

    # 2. バトル中のBGMリスト（「大地を揺るがす咆哮.oog」を削除しました）
    BATTLE_BGMS = [
        "飛翔.oog",
        "砂塵の城塞.oog"
    ]

    # 3. 効果音（SE）の読み込み
    se_cursor = None
    se_decide_battle = None

    try:
        se_cursor = pygame.mixer.Sound("着火音.oog")  # ✨ 移動音を「着火音.oog」に変更
        se_cursor.set_volume(SE_VOLUME)            # 🌟SE音量を 1.0 に設定
    except pygame.error:
        print("選択効果音(着火音.oog)が見つかりません。消音で続行します。")

    try:
        se_decide_battle = pygame.mixer.Sound("ホラ貝02.oog")  # ✨ BATTLE用の決定音を「ホラ貝02.oog」に
        se_decide_battle.set_volume(SE_VOLUME)                # 🌟SE音量を 1.0 に設定
    except pygame.error:
        print("決定効果音(ホラ貝02.oog)が見つかりません。消音で続行します。")


    # --- スタート画面・シーン管理の設定 ---
    game_state = "START_MENU"  # 初期状態はスタートメニュー

    menu_options = ["BATTLE STATE", "SANDBOX", "TUTORIAL", "2 PLAYERS", "HOW TO PLAY"]
    selected_menu_idx = 0      # 初期状態でおすすめの「BATTLE STATE」を選択

    # 背景の自動スライド用変数
    auto_scroll_dir = 1        # 1: 下へ移動, -1: 上へ移動
    AUTO_SCROLL_SPEED = 1.0    

    # --- マップとカメラの設定 ---
    MAP_WIDTH, MAP_HEIGHT = 4000, 3000
    camera_pos = pygame.math.Vector2(0, 0)
    EDGE_SCROLL_SPEED = 11  

    # 初期ズームを最小値（フィールドMAX表示）に設定
    MIN_ZOOM = 0.35   
    MAX_ZOOM = 0.5    
    zoom = MIN_ZOOM  
    last_zoom = zoom  

    try:
        orig_bg = pygame.image.load("heiti.PNG").convert()
        orig_bg = pygame.transform.scale(orig_bg, (MAP_WIDTH, MAP_HEIGHT))
    except:
        orig_bg = pygame.Surface((MAP_WIDTH, MAP_HEIGHT))
        orig_bg.fill((34, 139, 34))

    bg_image = pygame.transform.scale(orig_bg, (int(MAP_WIDTH * zoom), int(MAP_HEIGHT * zoom)))

    # --- 🏰 城（本部）の設定 ───
    CASTLE_SIZE = (500, 500) 
    castle_blue_pos = pygame.math.Vector2(300, 1450)
    castle_red_pos = pygame.math.Vector2(3720, 1450)

    # 味方の城画像の読み込み
    try:
        orig_castle_blue = pygame.image.load("castle_blue.png").convert_alpha()
        orig_castle_blue = pygame.transform.scale(orig_castle_blue, CASTLE_SIZE)
    except:
        orig_castle_blue = pygame.Surface(CASTLE_SIZE, pygame.SRCALPHA)
        orig_castle_blue.fill((0, 50, 200, 200))
        pygame.draw.rect(orig_castle_blue, (0, 200, 255), (0, 0, CASTLE_SIZE[0], CASTLE_SIZE[1]), 8)

    # 敵の城画像の読み込み
    try:
        orig_castle_red = pygame.image.load("castle_red.png").convert_alpha()
        orig_castle_red = pygame.transform.scale(orig_castle_red, CASTLE_SIZE)
    except:
        orig_castle_red = pygame.Surface(CASTLE_SIZE, pygame.SRCALPHA)
        orig_castle_red.fill((200, 0, 50, 200))
        pygame.draw.rect(orig_castle_red, (255, 100, 0), (0, 0, CASTLE_SIZE[0], CASTLE_SIZE[1]), 8)


    # --- グローバル状態管理用変数 ---
    is_aligning = False       
    is_rotating = False       
    formation_center = pygame.math.Vector2(0, 0)
    formation_angle = 0.0
    selected_groups = set()  

    group_saved_angles = {}
    group_saved_stages = {}
    group_saved_col_modes = {}
    group_target_enemies = {}  
    group_modes = {}  # 各グループのモード管理: "FORMATION" または "MELEE"

    is_dragging = False
    drag_start_pos = (0, 0)

    # --- カラー定義 ---
    COLOR_SHAFT = (139, 90, 43)   
    COLOR_TIP = (192, 192, 192)   
    COLOR_HILT = (0x5E, 0x48, 0x31)         
    COLOR_EDGE = (0xE0, 0xE0, 0xE0)         
    COLOR_BLADE_CENTER = (0xC0, 0xC0, 0xC0) 

    COLOR_LANCE_TIP = (0xD1, 0xD5, 0xDB)      
    COLOR_LANCE_GRIP = (0x1F, 0x29, 0x37)     
    COLOR_LANCE_ACCENT = (0xD9, 0x77, 0x06)   

    def get_spacing_by_stage(stage, unit_type):
        if unit_type in ("melee_infantry", "spearman"):
            base = 60  
        elif unit_type == "cavalry":
            base = 70  
        else:
            base = 45  
        if stage == 2: return base * 1.35  
        if stage == 3: return base * 1.75  
        return base  

    def calculate_actual_cols(mode, total_units):
        if total_units <= 0: return 1
        if mode == 4: return max(1, int(math.sqrt(total_units * 1.0)))
        elif mode == 5: return max(1, math.ceil(total_units / 3))
        elif mode == 6: return max(1, math.ceil(total_units / 4))
        elif mode == 7: return 3
        elif mode == 8: return 4
        return max(1, int(math.sqrt(total_units * 1.0)))

    # --- グリッドシステム ---
    GRID_SIZE = 150  
    def get_grid_key(pos):
        return (int(pos.x // GRID_SIZE), int(pos.y // GRID_SIZE))

    def update_grid_system(units):
        grid = {}
        for u in units:
            key = get_grid_key(u.pos)
            if key not in grid: grid[key] = []
            grid[key].append(u)
        return grid

    def get_target_counts(all_units):
        counts = {}
        for u in all_units:
            if u.alive and u.attack_target:
                counts[id(u.attack_target)] = counts.get(id(u.attack_target), 0) + 1
        return counts

    # --- ユニットクラス ---
    class Unit:
        def __init__(self, x, y, team, unit_type, group_id, is_captain=False):
            self.team = team  
            self.type = unit_type 
            self.group_id = group_id  
            self.pos = pygame.math.Vector2(x, y)
            self.vel = pygame.math.Vector2(0, 0)
            self.acc = pygame.math.Vector2(0, 0)
            self.target = pygame.math.Vector2(x, y) 
            self.angle = 0 if team == 0 else 180
            self.alive = True
            self.friction = 0.8  

            self.is_captain = is_captain  
            self.is_bearer = False  
            self.formation_index = 0  

            self.state = "IDLE"       
            self.attack_target = None 
            self.attacker_memory = None  
            
            self.cooldown_timer = 0         
            self.is_first_attack = True     
            self.attack_anim_frame = 0  
            self.is_alert = False          
            self.is_performing = False     
            self.spear_jitter = 0.0        
            self.stun_timer = 0             

            self.charge_hit_count = 0  
            self.jitter = pygame.math.Vector2(0, 0)
            self.jitter_ticks = random.randint(0, 100) 
            self.commanded = False
            self.individual_target_mode = False  

            self.search_timer = random.randint(0, 10)

            self.death_timer = 0
            self.death_duration = 90 

            if unit_type == "melee_infantry":
                self.hp = 50 if is_captain else 25       
                self.radius = 22    
                self.base_thrust = 0.95                 　
                self.mass = 4.0                         
                self.search_range = 700 
                self.attack_power = 1                   
                self.first_attack_delay = 12            
                self.attack_interval_max = 36           
                self.current_thrust = self.base_thrust
                self.consecutive_attack_counts = {}     
                self.reach = 60.0 
                
            elif unit_type == "spearman":
                self.hp = 60 if is_captain else 30       
                self.radius = 22    
                self.base_thrust = 0.85                 
                self.mass = 5.0                         
                self.search_range = 700 
                self.attack_power = 2       
                self.first_attack_delay = 12            
                self.attack_interval_max = 30 
                self.current_thrust = self.base_thrust
                self.hit_cavalry_ids = set()            
                self.reach = 180.0 
                
            elif unit_type == "cavalry":
                self.hp = 200 if is_captain else 100    
                self.radius = 24    
                self.base_thrust = 5.0                  
                self.max_thrust = 14.0                  
                self.mass = 20.0                        
                self.search_range = 800 
                self.attack_power = 3                   
                self.first_attack_delay = 6             
                self.attack_interval_max = 120          
                self.current_thrust = self.base_thrust  
                self.cavalry_stun_queue = []
                self.reach = 95.0 

            if team == 0:
                self.base_color = (0, 210, 255) if is_captain else (0, 0, 255) 
            else:
                self.base_color = (255, 140, 0) if is_captain else (255, 0, 0) 
            self.color = self.base_color

        def apply_force(self, force):
            if self.stun_timer > 0 or self.state == "DEAD": return 
            self.acc += force / self.mass

        def _calc_sword_state(self, frame, is_west=False):
            f = frame
            direction_factor = 1.0 if not is_west else -1.0
            if f < 18:
                p = f / 18.0
                offset = (math.radians(-15) * direction_factor) * math.sin(p * math.pi / 2)
                pseudo_len_factor = 1.0 + 0.15 * math.sin(p * math.pi / 2)  
            elif f < 21:
                p = (f - 18) / 3.0
                start_ang = math.radians(-15) * direction_factor
                end_ang = math.radians(165) * direction_factor
                offset = start_ang + (end_ang - start_ang) * p
                pseudo_len_factor = 1.15 - 0.25 * p  
            else:
                p = (f - 21) / 15.0
                start_ang = math.radians(165) * direction_factor
                end_ang = (math.radians(30) * direction_factor)
                offset = start_ang + (end_ang - start_ang) * p
                pseudo_len_factor = 0.9 + 0.1 * p
            return (math.radians(-90) + offset), pseudo_len_factor

        def update(self, enemies, current_target_counts):
            if self.state == "DEAD":
                self.death_timer += 1
                self.vel *= 0.1 
                self.pos += self.vel
                if self.death_timer >= self.death_duration:
                    self.alive = False
                return

            self.jitter_ticks += 1
            pulse = math.sin(self.jitter_ticks * 0.08) * 0.45
            heartbeat = 0.0
            if self.jitter_ticks % 45 < 8:
                heartbeat = math.sin((self.jitter_ticks % 45) * (math.pi / 8)) * 0.6
            total_jitter = pulse + heartbeat
            self.jitter = pygame.math.Vector2(
                math.cos(math.radians(self.angle)) * total_jitter,
                math.sin(math.radians(self.angle)) * total_jitter
            )
            self.spear_jitter = math.sin(self.jitter_ticks * 0.12) * math.radians(1.5)

            if self.type == "cavalry" and self.cavalry_stun_queue:
                for stun_f, thrust_debuff in self.cavalry_stun_queue:
                    self.stun_timer += stun_f
                    self.current_thrust = max(self.base_thrust, self.current_thrust - thrust_debuff)
                self.cavalry_stun_queue.clear()

            if self.stun_timer > 0:
                self.stun_timer -= 1
                self.acc *= 0
                return

            if self.cooldown_timer > 0:
                self.cooldown_timer -= 1

            if (self.attack_target and self.state in ("CHARGE", "COOLDOWN", "STAY_ATTACK")) or self.is_performing:
                self.attack_anim_frame += 1
                if self.attack_anim_frame >= self.attack_interval_max:  
                    self.attack_anim_frame = 0
            else:
                self.attack_anim_frame = 0

            if self.attacker_memory and (self.attacker_memory.state == "DEAD" or self.attacker_memory.hp <= 0):
                self.attacker_memory = None

            mode = group_modes.get(self.group_id, "FORMATION")

            if mode == "FORMATION":
                self.individual_target_mode = False
                dist_to_slot_sq = self.pos.distance_squared_to(self.target)

                if dist_to_slot_sq > 4:  
                    dir_to_slot = (self.target - self.pos).normalize()
                    self.apply_force(dir_to_slot * self.base_thrust * 3.5)
                    self.state = "MOVE"
                    if self.is_performing and self.type == "spearman":
                        self.angle = -90
                    else:
                        self.angle = math.degrees(math.atan2(dir_to_slot.y, dir_to_slot.x))
                else:
                    self.state = "IDLE"
                    self.vel *= 0.1
                    if self.is_performing and self.type == "spearman":
                        self.angle = -90
                    elif self.group_id in group_saved_angles:
                        self.angle = math.degrees(group_saved_angles[self.group_id])

                self.search_timer += 1
                if self.search_timer >= 10:
                    self.search_timer = 0
                    self.attack_target = None
                    closest_enemy = None
                    reach_limit = self.radius + 22 + self.reach 
                    closest_dist_sq = reach_limit * reach_limit
                    
                    for e in enemies:
                        if e.state != "DEAD":
                            d_sq = self.pos.distance_squared_to(e.pos)
                            if d_sq < closest_dist_sq:
                                closest_dist_sq = d_sq
                                closest_enemy = e
                    
                    if closest_enemy:
                        self.attack_target = closest_enemy

                if self.attack_target:
                    self.state = "STAY_ATTACK"  
                    to_enemy = self.attack_target.pos - self.pos
                    self.angle = math.degrees(math.atan2(to_enemy.y, to_enemy.x))
            else:
                if self.attack_target and (self.attack_target.state == "DEAD" or self.attack_target.hp <= 0):
                    self.attack_target = None
                    self.individual_target_mode = False

                self.search_timer += 1
                if self.search_timer >= 10:
                    self.search_timer = 0
                    
                    if not self.individual_target_mode:
                        if self.attacker_memory and self.attacker_memory.state != "DEAD" and self.attacker_memory.hp > 0:
                            self.attack_target = self.attacker_memory
                        else:
                            closest_enemy = None
                            closest_dist_sq = self.search_range * self.search_range
                            for e in enemies:
                                if e.state != "DEAD":
                                    limit = 5 if e.type == "cavalry" else 2
                                    if current_target_counts.get(id(e), 0) < limit:
                                        d_sq = self.pos.distance_squared_to(e.pos)
                                        if d_sq < closest_dist_sq:
                                            closest_dist_sq = d_sq
                                            closest_enemy = e
                            if closest_enemy:
                                self.attack_target = closest_enemy

                if self.attack_target:
                    self.state = "CHARGE"
                    to_enemy = self.attack_target.pos - self.pos
                    dist_sq = to_enemy.length_squared()
                    dir_vec = to_enemy.normalize() if dist_sq > 0 else pygame.math.Vector2(1, 0)
                    self.angle = math.degrees(math.atan2(dir_vec.y, dir_vec.x))
                    
                    stop_range = self.radius + 22 + (self.reach * 0.8)
                    if dist_sq > (stop_range ** 2):
                        if self.type == "cavalry":
                            self.current_thrust = min(self.max_thrust, self.current_thrust + 0.15)
                            self.apply_force(dir_vec * self.current_thrust * 2.5)
                        else:
                            self.apply_force(dir_vec * self.current_thrust * 2.5)
                    else:
                        self.vel *= 0.4 
                else:
                    self.state = "IDLE"
                    self.vel *= 0.4

            self.vel += self.acc
            self.pos += self.vel
            
            if self.pos.x < self.radius: self.pos.x = self.radius; self.vel.x *= -0.2
            elif self.pos.x > MAP_WIDTH - self.radius: self.pos.x = MAP_WIDTH - self.radius; self.vel.x *= -0.2
            if self.pos.y < self.radius: self.pos.y = self.radius; self.vel.y *= -0.2
            elif self.pos.y > MAP_HEIGHT - self.radius: self.pos.y = MAP_HEIGHT - self.radius; self.vel.y *= -0.2

            self.vel *= self.friction
            self.acc *= 0

        def draw(self, surface, cam, current_zoom, is_selected):
            sx = int((self.pos.x + self.jitter.x - cam.x) * current_zoom)
            sy = int((self.pos.y + self.jitter.y - cam.y) * current_zoom)
            r = max(2, int(self.radius * current_zoom)) 
            
            if not (-100 < sx < WIDTH + 100 and -100 < sy < HEIGHT + 100): return

            if self.state == "DEAD":
                progress = self.death_timer / self.death_duration
                r_c = int(self.base_color[0] + (255 - self.base_color[0]) * progress)
                g_c = int(self.base_color[1] + (255 - self.base_color[1]) * progress)
                b_c = int(self.base_color[2] + (255 - self.base_color[2]) * progress)
                self.color = (r_c, g_c, b_c)
                alpha = int(255 * (1.0 - progress))
                temp_surf = pygame.Surface((r * 8 + 400, r * 8 + 400), pygame.SRCALPHA)
                cx_local, cy_local = temp_surf.get_width() // 2, temp_surf.get_height() // 2
                pygame.draw.circle(temp_surf, self.color, (cx_local, cy_local), r)
                temp_surf.set_alpha(alpha)
                surface.blit(temp_surf, (sx - cx_local, sy - cy_local))
                return 

            if is_selected and group_modes.get(self.group_id, "FORMATION") == "FORMATION":
                pygame.draw.circle(surface, (255, 255, 255), (sx, sy), r + max(1, int(4 * current_zoom)), 2)
            
            rad = math.radians(self.angle)

            if self.type == "cavalry":
                length = max(8, int(44 * current_zoom)) 
                width = max(5, int(22 * current_zoom))  
                cos_a, sin_a = math.cos(rad), math.sin(rad)
                local_pts = [(length // 2, -width // 2), (length // 2, width // 2), (-length // 2, width // 2), (-length // 2, -width // 2)]
                rotated_pts = [(sx + int(lx * cos_a - ly * sin_a), sy + int(lx * sin_a + ly * cos_a)) for lx, ly in local_pts]
                pygame.draw.polygon(surface, self.color, rotated_pts)
                
                f = self.attack_anim_frame
                lance_slide = 0.0
                if 0 < f < 15:
                    p = f / 15.0
                    lance_slide = 12 * math.sin(p * math.pi) * current_zoom  

                right_hand_angle = rad + math.pi / 2.3
                hand_offset = r * 0.7
                lx_base = sx + int(hand_offset * math.cos(right_hand_angle))
                ly_base = sy + int(hand_offset * math.sin(right_hand_angle))

                lance_len = self.reach * current_zoom
                l_cos, l_sin = math.cos(rad), math.sin(rad)
                l_perp_x, l_perp_y = -l_sin, l_cos

                p_grip = lance_slide
                p_ring = p_grip + 20 * current_zoom
                p_mid = p_grip + 65 * current_zoom
                p_tip = p_grip + lance_len

                w_grip = 1.8 * current_zoom
                w_ring = 3.6 * current_zoom
                w_mid = 4.5 * current_zoom
                w_tip = 0.4 * current_zoom

                pts_right = [
                    (lx_base + p_grip*l_cos + w_grip*l_perp_x, ly_base + p_grip*l_sin + w_grip*l_perp_y),
                    (lx_base + p_ring*l_cos + w_ring*l_perp_x, ly_base + p_ring*l_sin + w_ring*l_perp_y),
                    (lx_base + p_mid*l_cos + w_mid*l_perp_x, ly_base + p_mid*l_sin + w_mid*l_perp_y),
                    (lx_base + p_tip*l_cos + w_tip*l_perp_x, ly_base + p_tip*l_sin + w_tip*l_perp_y)
                ]
                pts_left = [
                    (lx_base + p_tip*l_cos - w_tip*l_perp_x, ly_base + p_tip*l_sin - w_tip*l_perp_y),
                    (lx_base + p_mid*l_cos - w_mid*l_perp_x, ly_base + p_mid*l_sin - w_mid*l_perp_y),
                    (lx_base + p_ring*l_cos - w_ring*l_perp_x, ly_base + p_ring*l_sin - w_ring*l_perp_y),
                    (lx_base + p_grip*l_cos - w_grip*l_perp_x, ly_base + p_grip*l_sin - w_grip*l_perp_y)
                ]
                pygame.draw.polygon(surface, COLOR_LANCE_GRIP, [pts_right[0], pts_right[2], pts_left[1], pts_left[3]])
                pygame.draw.polygon(surface, COLOR_LANCE_ACCENT, [pts_right[0], pts_right[1], pts_left[2], pts_left[3]])
                pygame.draw.polygon(surface, COLOR_LANCE_TIP, [pts_right[2], pts_right[3], pts_left[0], pts_left[1]])
            else:
                pygame.draw.circle(surface, self.color, (sx, sy), r)
            
            ex = sx + int(r * math.cos(rad))
            ey = sy + int(r * math.sin(rad))
            pygame.draw.line(surface, (255, 255, 255), (sx, sy), (ex, ey), max(1, int(2 * current_zoom)))

            if self.type == "spearman":
                base_spear_len = self.reach * current_zoom  
                
                if self.is_performing:
                    spear_angle = -math.pi / 2
                    current_rear_ratio = 0.12  
                elif self.attack_target:
                    to_enemy = self.attack_target.pos - self.pos
                    spear_angle = math.atan2(to_enemy.y, to_enemy.x)
                    current_rear_ratio = 0.20  
                else:
                    spear_angle = rad + self.spear_jitter if self.is_alert else -math.pi / 2 + self.spear_jitter
                    current_rear_ratio = 0.12 if not self.is_alert else 0.20

                f = self.attack_anim_frame
                is_active_thrust = (self.attack_target and self.state in ("CHARGE", "COOLDOWN", "STAY_ATTACK")) or self.is_performing
                
                if is_active_thrust and f > 0 and not self.is_performing:
                    if f < 12:  
                        p = f / 12.0
                        current_rear_ratio = 0.20 + (0.10 * p)
                    elif f < 18:  
                        p = (f - 12) / 6.0
                        current_rear_ratio = 0.30 - (0.25 * p)
                    else:  
                        p = (f - 18) / 12.0
                        current_rear_ratio = 0.05 + (0.15 * p)

                rear_len = base_spear_len * current_rear_ratio
                front_len = base_spear_len - rear_len

                right_hand_angle = rad + math.pi / 2
                hand_offset = r * 0.7  
                hx = sx + int(hand_offset * math.cos(right_hand_angle))
                hy = sy + int(hand_offset * math.sin(right_hand_angle))

                spear_start_x = hx - int(rear_len * math.cos(spear_angle))
                spear_start_y = hy - int(rear_len * math.sin(spear_angle))
                spear_end_x = hx + int(front_len * math.cos(spear_angle))
                spear_end_y = hy + int(front_len * math.sin(spear_angle))

                blade_start_len = max(0, front_len - (base_spear_len * 0.08)) 
                s_mid_x = hx + int(blade_start_len * math.cos(spear_angle))
                s_mid_y = hy + int(blade_start_len * math.sin(spear_angle))

                pygame.draw.line(surface, COLOR_SHAFT, (spear_start_x, spear_start_y), (s_mid_x, s_mid_y), max(2, int(4 * current_zoom)))
                pygame.draw.line(surface, COLOR_TIP, (s_mid_x, s_mid_y), (spear_end_x, spear_end_y), max(3, int(6 * current_zoom)))

            elif self.type == "melee_infantry":
                f = self.attack_anim_frame
                is_active_swing = (self.attack_target and self.state in ("CHARGE", "COOLDOWN", "STAY_ATTACK")) or self.is_performing
                cos_dir = math.cos(rad)
                is_west = cos_dir < 0  

                if is_active_swing and f >= 1:
                    final_sword_angle, len_factor = self._calc_sword_state(f, is_west)
                else:
                    final_sword_angle = rad + self.spear_jitter
                    len_factor = 1.0

                right_hand_angle = rad + math.pi / 2
                hand_offset = r * 0.7
                hx = sx + int(hand_offset * math.cos(right_hand_angle))
                hy = sy + int(hand_offset * math.sin(right_hand_angle))

                cos_s, sin_s = math.cos(final_sword_angle), math.sin(final_sword_angle)
                sz = current_zoom
                blade_len = self.reach * sz * len_factor  
                blade_w = 3.5 * sz  

                g_len = 22 * sz
                cos_perp, sin_perp = math.cos(final_sword_angle + math.pi/2), math.sin(final_sword_angle + math.pi/2)
                g_p1 = (hx - g_len * cos_s - 3*sz * cos_perp, hy - g_len * sin_s - 3*sz * sin_perp)
                g_p2 = (hx - g_len * cos_s + 3*sz * cos_perp, hy - g_len * sin_s + 3*sz * sin_perp)
                g_p3 = (hx + 3*sz * cos_perp, hy + 3*sz * sin_perp)
                g_p4 = (hx - 3*sz * cos_perp, hy - 3*sz * sin_perp)
                pygame.draw.polygon(surface, COLOR_HILT, [g_p1, g_p2, g_p3, g_p4])

                cross_w = 14 * sz
                cross_h = 3.5 * sz
                c_p1 = (hx - cross_w * cos_perp, hy - cross_w * sin_perp)
                c_p2 = (hx + cross_w * cos_perp, hy + cross_w * sin_perp)
                c_p3 = (hx + cross_h * cos_s + cross_w * cos_perp, hy + cross_h * sin_s + cross_w * sin_perp)
                c_p4 = (hx + cross_h * cos_s - cross_w * cos_perp, hy + cross_h * sin_s - cross_w * sin_perp)
                pygame.draw.polygon(surface, COLOR_EDGE, [c_p1, c_p2, c_p3, c_p4])

                b_base_left = (hx + 3.5 * sz * cos_s - blade_w * cos_perp, hy + 3.5 * sz * sin_s - blade_w * sin_perp)
                b_base_right = (hx + 3.5 * sz * cos_s + blade_w * cos_perp, hy + 3.5 * sz * sin_s + blade_w * sin_perp)
                b_center_line = (hx + (3.5 * sz + blade_len * 0.8) * cos_s, hy + (3.5 * sz + blade_len * 0.8) * sin_s)
                b_tip = (hx + (3.5 * sz + blade_len) * cos_s, hy + (3.5 * sz + blade_len) * sin_s)

                pygame.draw.polygon(surface, COLOR_BLADE_CENTER, [b_base_left, b_base_right, b_center_line])
                pygame.draw.line(surface, COLOR_EDGE, b_base_left, b_center_line, max(1, int(1.5 * sz)))
                pygame.draw.line(surface, COLOR_EDGE, b_base_right, b_center_line, max(1, int(1.5 * sz)))
                pygame.draw.line(surface, COLOR_EDGE, b_center_line, b_tip, max(1, int(1.5 * sz)))

            if self.is_bearer:
                flag_w, flag_h = int(35 * current_zoom), int(24 * current_zoom)
                flag_y = sy - r - flag_h - int(8 * current_zoom)
                pygame.draw.line(surface, (220, 220, 220), (sx, sy - r), (sx, flag_y), max(1, int(3 * current_zoom)))
                pygame.draw.rect(surface, (255, 255, 0) if self.team == 0 else (255, 0, 255), (sx, flag_y, flag_w, flag_h))

            max_hp = 200 if (self.type == "cavalry" and self.is_captain) else (100 if self.type == "cavalry" else (50 if (self.type == "melee_infantry" and self.is_captain) else (60 if (self.type == "spearman" and self.is_captain) else (25 if self.type == "melee_infantry" else 30))))
            bw = int((55 if self.is_captain else 35) * current_zoom)
            bh = max(1, int(4 * current_zoom))
            if bw > 5: 
                pygame.draw.rect(surface, (200, 0, 0), (sx - bw//2, sy - r - bh - 6, bw, bh))
                pygame.draw.rect(surface, (0, 200, 0), (sx - bw//2, sy - r - bh - 6, int((max(0, self.hp) / max_hp) * bw), bh))


    def apply_formation_to_multiple_groups(all_units, group_ids, center, angle, clear_velocity=False, is_initial=False):
        global group_saved_angles, group_saved_stages, group_saved_col_modes
        current_center = pygame.math.Vector2(center)
        for g_id in group_ids:
            if group_modes.get(g_id, "FORMATION") == "MELEE": continue  
            group_saved_angles[g_id] = angle
            units = [u for u in all_units if u.group_id == g_id and u.state != "DEAD"]
            if not units: continue
            
            stage = group_saved_stages.get(g_id, 1)
            spacing = get_spacing_by_stage(stage, units[0].type)
            col_mode = group_saved_col_modes.get(g_id, 4)
            n = len(units)
            cols = calculate_actual_cols(col_mode, n)
            rows = math.ceil(n / cols)
            
            for u in units:
                i = u.formation_index
                c, r = i % cols, i // cols
                ox = (c - (cols-1)/2) * spacing
                oy = (r - (rows-1)/2) * spacing
                rx = ox * math.cos(angle) - oy * math.sin(angle)
                ry = ox * math.sin(angle) + oy * math.cos(angle)
                
                u.target = current_center + pygame.math.Vector2(rx, ry)
                u.attack_target = None
                if not is_initial:
                    u.state = "MOVE"
                    u.commanded = True
                else:
                    u.pos = pygame.math.Vector2(u.target)
                    u.state = "IDLE"
                if clear_velocity: u.vel *= 0
                
            offset_y = (rows * spacing) + 60
            rx_offset = 0 * math.cos(angle) - offset_y * math.sin(angle)
            ry_offset = 0 * math.sin(angle) + offset_y * math.cos(angle)
            current_center += pygame.math.Vector2(rx_offset, ry_offset)


    def draw_formation_ui(surface, units, cam, current_zoom, center=None, angle=0.0, is_preview=False, preview_stage=None, preview_col_mode=None):
        global group_saved_angles, group_saved_stages, group_saved_col_modes
        units = [u for u in units if u.state != "DEAD"]
        if not units: return
        g_id = units[0].group_id
        if group_modes.get(g_id, "FORMATION") == "MELEE": return  
        
        n = len(units)
        stage = preview_stage if is_preview else group_saved_stages.get(g_id, 1)
        spacing = get_spacing_by_stage(stage, units[0].type)
        col_mode = preview_col_mode if is_preview else group_saved_col_modes.get(g_id, 4)
        cols = calculate_actual_cols(col_mode, n)
        rows = math.ceil(n / cols)
        
        base_r = 24 if units[0].type == "cavalry" else 22
        w = (cols - 1) * spacing + (base_r * 2 + 15)
        h = (rows - 1) * spacing + (base_r * 2 + 15)

        if center is None:
            avg_t = pygame.math.Vector2(0, 0)
            for u in units: avg_t += u.target
            center = avg_t / n
            angle = group_saved_angles.get(g_id, 0.0)

        corners = [pygame.math.Vector2(w/2, -h/2), pygame.math.Vector2(w/2, h/2), pygame.math.Vector2(-w/2, h/2), pygame.math.Vector2(-w/2, -h/2)]
        screen_pts = []
        for p in corners:
            rx = p.x * math.cos(angle) - p.y * math.sin(angle)
            ry = p.x * math.sin(angle) + p.y * math.cos(angle)
            world_pt = center + pygame.math.Vector2(rx, ry)
            sx = int((world_pt.x - cam.x) * current_zoom)
            sy = int((world_pt.y - cam.y) * current_zoom)
            screen_pts.append((sx, sy))
            
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        fill_color = (0, 255, 120, 45) if is_preview else (255, 255, 255, 20)
        line_color = (0, 255, 120, 180) if is_preview else (255, 255, 255, 70)
        pygame.draw.polygon(overlay, fill_color, screen_pts) 
        pygame.draw.polygon(overlay, line_color, screen_pts, 2)
        pygame.draw.line(overlay, (255, 30, 30), screen_pts[0], screen_pts[1], max(2, int(5 * current_zoom)))
        surface.blit(overlay, (0, 0))

    def get_groups_center(all_units, group_ids):
        units = [u for u in all_units if u.group_id in group_ids and u.state != "DEAD"]
        if not units: return pygame.math.Vector2(0, 0)
        avg = pygame.math.Vector2(0, 0)
        for u in units: avg += u.pos
        return avg / len(units)

    def draw_lockon_cursor(surface, mx, my, is_over_friend, is_over_enemy, current_mode="FORMATION"):
        color = (0, 255, 120) if is_over_friend else ((255, 0, 0) if is_over_enemy else (255, 230, 0))
        if current_mode == "MELEE":
            color = (255, 50, 255) if is_over_enemy else (200, 50, 255) 
        pygame.draw.circle(surface, color, (mx, my), 6, 2)
        for i in range(4):
            pygame.draw.arc(surface, color, (mx-16, my-16, 32, 32), math.radians(i*90+20), math.radians(i*90+70), 2)
        pygame.draw.line(surface, color, (mx - 22, my), (mx - 10, my), 2)
        pygame.draw.line(surface, color, (mx + 10, my), (mx + 22, my), 2)
        pygame.draw.line(surface, color, (mx, my - 22), (mx, my - 10), 2)
        pygame.draw.line(surface, color, (mx, my + 10), (mx, my + 22), 2)

    def spawn_grid_with_captain(center_x, center_y, count, cols, team, unit_type, group_id):
        units = []
        spacing = 60 if unit_type in ("melee_infantry", "spearman") else 70
        rows = (count + cols - 1) // cols
        actual_cols = min(count, cols)
        total_width = (actual_cols - 1) * spacing
        total_height = (rows - 1) * spacing
        
        start_x = center_x - (total_width / 2)
        start_y = center_y - (total_height / 2)
        
        captain = Unit(start_x, start_y, team, unit_type, group_id, is_captain=True)
        captain.formation_index = 0
        units.append(captain) 
        
        for i in range(1, count):
            c, r = i % cols, i // cols
            u = Unit(start_x + c * spacing, start_y + r * spacing, team, unit_type, group_id, is_captain=False)
            u.formation_index = i
            units.append(u)
            
        soldiers = [u for u in units if not u.is_captain]
        if soldiers: 
            random.choice(soldiers).is_bearer = True
            
        return units

    # --- 部隊初期配置 ---
    all_units = []

    # 青 味方陣営（TEAM 0）
    all_units.extend(spawn_grid_with_captain(920,  500,  9, 3, 0, "cavalry", 0))
    all_units.extend(spawn_grid_with_captain(920,  2500, 9, 3, 0, "cavalry", 1))
    all_units.extend(spawn_grid_with_captain(1020, 1500,  72, 3, 0, "spearman", 2)) 
    all_units.extend(spawn_grid_with_captain(720,  1500, 25, 5, 0, "melee_infantry", 3)) 
    all_units.extend(spawn_grid_with_captain(720,  1050, 16, 4, 0, "melee_infantry", 4)) 
    all_units.extend(spawn_grid_with_captain(720,  1950, 16, 4, 0, "melee_infantry", 5)) 

    # 赤 敵陣営（TEAM 1）
    all_units.extend(spawn_grid_with_captain(3100, 500,  9, 3, 1, "cavalry", 6))
    all_units.extend(spawn_grid_with_captain(3100, 2500, 9, 3, 1, "cavalry", 7))
    all_units.extend(spawn_grid_with_captain(3000, 1500,  72, 3, 1, "spearman", 8)) 
    all_units.extend(spawn_grid_with_captain(3300, 1500, 25, 5, 1, "melee_infantry", 9))  
    all_units.extend(spawn_grid_with_captain(3300, 1050, 16, 4, 1, "melee_infantry", 10)) 
    all_units.extend(spawn_grid_with_captain(3300, 1950, 16, 4, 1, "melee_infantry", 11)) 

    for g_id in range(12):
        group_saved_angles[g_id] = 0.0 if g_id < 6 else math.pi
        group_target_enemies[g_id] = None
        group_saved_stages[g_id] = 1
        group_saved_col_modes[g_id] = 4  
        if g_id in (2, 8):
            group_saved_col_modes[g_id] = 7  
        if g_id < 6:
            group_modes[g_id] = "FORMATION"
        else:
            group_modes[g_id] = "MELEE"
            
    for g_id in range(12):
        g_units = [u for u in all_units if u.group_id == g_id]
        if g_units:
            avg_pos = pygame.math.Vector2(0, 0)
            for u in g_units: avg_pos += u.pos
            avg_pos /= len(g_units)
            apply_formation_to_multiple_groups(all_units, {g_id}, avg_pos, group_saved_angles[g_id], clear_velocity=True, is_initial=True)

    current_global_stage = 1
    current_global_col_mode = 4  
    reassign_timer = 0

    # --- メインループ ---
    running = True
    while running:
        keys = pygame.key.get_pressed()
        
        # ズーム変更
        if keys[pygame.K_q]: zoom = min(MAX_ZOOM, zoom + 0.005)
        if keys[pygame.K_w]: zoom = max(MIN_ZOOM, zoom - 0.005)

        if keys[pygame.K_1] or keys[pygame.K_KP1]: current_global_stage = 1
        if keys[pygame.K_2] or keys[pygame.K_KP2]: current_global_stage = 2
        if keys[pygame.K_3] or keys[pygame.K_KP3]: current_global_stage = 3

        if keys[pygame.K_4] or keys[pygame.K_KP4]: current_global_col_mode = 4 
        if keys[pygame.K_5] or keys[pygame.K_KP5]: current_global_col_mode = 5 
        if keys[pygame.K_6] or keys[pygame.K_KP6]: current_global_col_mode = 6 
        if keys[pygame.K_7] or keys[pygame.K_KP7]: current_global_col_mode = 7 
        if keys[pygame.K_8] or keys[pygame.K_KP8]: current_global_col_mode = 8 

        if selected_groups:
            for g_id in selected_groups:
                group_saved_stages[g_id] = current_global_stage
                group_saved_col_modes[g_id] = current_global_col_mode

        if zoom != last_zoom:
            bg_image = pygame.transform.scale(orig_bg, (int(MAP_WIDTH * zoom), int(MAP_HEIGHT * zoom)))
            last_zoom = zoom

        mx, my = pygame.mouse.get_pos()
        
        # --- カメラ制御 ---
        if game_state == "START_MENU":
            camera_pos.y += AUTO_SCROLL_SPEED * auto_scroll_dir
            max_cam_y = MAP_HEIGHT - HEIGHT / zoom
            
            if camera_pos.y >= max_cam_y:
                camera_pos.y = max_cam_y
                auto_scroll_dir = -1
            elif camera_pos.y <= 0:
                camera_pos.y = 0
                auto_scroll_dir = 1
        else:
            KEY_SCROLL_SPEED = 15  
            if keys[pygame.K_LEFT]:  camera_pos.x -= KEY_SCROLL_SPEED / zoom
            if keys[pygame.K_RIGHT]: camera_pos.x += KEY_SCROLL_SPEED / zoom
            if keys[pygame.K_UP]:    camera_pos.y -= KEY_SCROLL_SPEED / zoom
            if keys[pygame.K_DOWN]:  camera_pos.y += KEY_SCROLL_SPEED / zoom

            if mx < 20:          camera_pos.x -= EDGE_SCROLL_SPEED / zoom
            if mx > WIDTH - 20:  camera_pos.x += EDGE_SCROLL_SPEED / zoom
            if my < 20:          camera_pos.y -= EDGE_SCROLL_SPEED / zoom
            if my > HEIGHT - 20: camera_pos.y += EDGE_SCROLL_SPEED / zoom

        camera_pos.x = max(0.0, min(camera_pos.x, MAP_WIDTH - WIDTH / zoom))
        camera_pos.y = max(0.0, min(camera_pos.y, MAP_HEIGHT - HEIGHT / zoom))
        
        world_mouse = camera_pos + (pygame.math.Vector2(mx, my) / zoom)

        friends = [u for u in all_units if u.team == 0]
        enemies = [u for u in all_units if u.team == 1]
        
        current_active_mode = "FORMATION"
        if selected_groups:
            current_active_mode = group_modes.get(list(selected_groups)[0], "FORMATION")

        current_target_counts = get_target_counts(all_units)
        unit_grid = update_grid_system(all_units)
        
        is_over_friend, is_over_enemy = False, False
        hovered_unit = None
        
        cx, cy = get_grid_key(world_mouse)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                key = (cx + dx, cy + dy)
                if key in unit_grid:
                    for u in unit_grid[key]:
                        if u.state != "DEAD" and u.pos.distance_squared_to(world_mouse) < ((u.radius + 15) ** 2):
                            hovered_unit = u
                            if u.team == 0: is_over_friend = True
                            else: is_over_enemy = True
                            break

        # --- イベント処理 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if game_state == "START_MENU":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        selected_menu_idx = (selected_menu_idx - 1) % len(menu_options)
                        if se_cursor: se_cursor.play()  
                    elif event.key == pygame.K_DOWN:
                        selected_menu_idx = (selected_menu_idx + 1) % len(menu_options)
                        if se_cursor: se_cursor.play()  
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        chosen = menu_options[selected_menu_idx]
                        
                        # 🌟 項目ごとの決定音分岐（BATTLE STATEの時だけホラ貝が鳴る）
                        if chosen == "BATTLE STATE":
                            if se_decide_battle: se_decide_battle.play()
                            
                            game_state = "PLAYING"
                            pygame.mixer.music.stop()       
                            
                            # ランダムでバトル曲を選んでループ再生
                            chosen_battle_bgm = random.choice(BATTLE_BGMS)
                            try:
                                pygame.mixer.music.load(chosen_battle_bgm)
                                pygame.mixer.music.play(-1)
                                pygame.mixer.music.set_volume(BGM_VOLUME)  # 再生時に音量を 0.8 に再設定
                                print(f"BGM再生開始: {chosen_battle_bgm}")
                            except pygame.error:
                                print(f"バトルBGM({chosen_battle_bgm})の読み込みに失敗しました。")
                                
                        elif chosen == "SANDBOX":
                            # ここに将来的に別の決定音を追加できます
                            # if se_decide_sandbox: se_decide_sandbox.play()
                            game_state = "PLAYING"
                            pygame.mixer.music.stop()
                            chosen_battle_bgm = random.choice(BATTLE_BGMS)
                            try:
                                pygame.mixer.music.load(chosen_battle_bgm)
                                pygame.mixer.music.play(-1)
                                pygame.mixer.music.set_volume(BGM_VOLUME)
                            except pygame.error:
                                pass
                        else:
                            print(f"{chosen} が選択されました（未実装・決定音なし）")
                            
                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                    continue

            if game_state == "PLAYING":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_b and selected_groups:
                        for g_id in selected_groups:
                            if group_modes[g_id] == "FORMATION":
                                group_modes[g_id] = "MELEE"
                            else:
                                group_modes[g_id] = "FORMATION"
                    
                    if event.key == pygame.K_a and selected_groups:
                        for u in friends:
                            if u.group_id in selected_groups and u.type == "spearman" and u.state != "DEAD":
                                u.is_alert = not u.is_alert
                    if event.key == pygame.K_RETURN and selected_groups:
                        for u in friends:
                            if u.group_id in selected_groups and u.type in ("spearman", "melee_infantry") and u.state != "DEAD":
                                u.is_performing = not u.is_performing
                                if u.is_performing: u.attack_anim_frame = random.randint(0, 20)

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1: 
                        if is_aligning: 
                            is_rotating = True
                        else:
                            if is_over_friend:
                                selected_groups = {hovered_unit.group_id}
                                current_global_stage = group_saved_stages.get(hovered_unit.group_id, 1)
                                current_global_col_mode = group_saved_col_modes.get(hovered_unit.group_id, 4)
                            elif is_over_enemy and hovered_unit and selected_groups:
                                if current_active_mode == "MELEE":
                                    best_u = None
                                    best_d_sq = float('inf')
                                    for u in friends:
                                        if u.group_id in selected_groups and u.state != "DEAD":
                                            d_sq = u.pos.distance_squared_to(hovered_unit.pos)
                                            if d_sq < best_d_sq:
                                                best_d_sq = d_sq
                                                best_u = u
                                    if best_u:
                                        best_u.attack_target = hovered_unit
                                        best_u.individual_target_mode = True  
                                else:
                                    for g_id in selected_groups:
                                        group_target_enemies[g_id] = hovered_unit.group_id
                                        for u in friends:
                                            if u.group_id == g_id and u.state != "DEAD":
                                                u.attack_target = hovered_unit 
                            else:
                                is_dragging = True
                                drag_start_pos = (mx, my)
                    elif event.button == 3 and selected_groups:
                        if current_active_mode == "FORMATION":
                            is_aligning, is_rotating = True, False
                            formation_center = pygame.math.Vector2(world_mouse)

                            for g_id in selected_groups:
                                group_target_enemies[g_id] = None
                                alive_soldiers = [u for u in friends if u.group_id == g_id and u.state != "DEAD"]
                                if not alive_soldiers: continue
                                
                                captain_unit = next((u for u in alive_soldiers if u.is_captain), None)
                                regular_soldiers = [u for u in alive_soldiers if not u.is_captain]
                                regular_soldiers.sort(key=lambda u: u.formation_index)
                                
                                if captain_unit:
                                    captain_unit.formation_index = 0
                                for idx, u in enumerate(regular_soldiers):
                                    u.formation_index = (idx + 1) if captain_unit else idx

                            formation_angle = group_saved_angles.get(list(selected_groups)[0], 0.0)
                            for g_id in selected_groups: group_target_enemies[g_id] = None

                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if is_dragging:
                        is_dragging = False
                        x1, y1 = min(drag_start_pos[0], mx), min(drag_start_pos[1], my)
                        x2, y2 = max(drag_start_pos[0], mx), max(drag_start_pos[1], my)
                        world_p1 = camera_pos + (pygame.math.Vector2(x1, y1) / zoom)
                        world_p2 = camera_pos + (pygame.math.Vector2(x2, y2) / zoom)
                        
                        new_selection = set()
                        for u in friends:
                            if u.state != "DEAD" and world_p1.x <= u.pos.x <= world_p2.x and world_p1.y <= u.pos.y <= world_p2.y:
                                new_selection.add(u.group_id)
                        if new_selection:
                            selected_groups = new_selection
                            current_global_stage = group_saved_stages.get(list(new_selection)[0], 1)
                            current_global_col_mode = group_saved_col_modes.get(list(new_selection)[0], 4)
                        else:
                            selected_groups = set()
                    elif is_aligning and is_rotating:
                        for g_id in selected_groups:
                            group_saved_stages[g_id] = current_global_stage
                            group_saved_col_modes[g_id] = current_global_col_mode
                        apply_formation_to_multiple_groups(all_units, selected_groups, formation_center, formation_angle)
                        is_aligning, is_rotating = False, False

        if game_state == "PLAYING" and is_aligning and is_rotating:
            mouse_dir = world_mouse - formation_center
            if mouse_dir.length_squared() > 25: formation_angle = math.atan2(mouse_dir.y, mouse_dir.x)

        # --- 衝突判定 ＆ 移動更新 ---
        if game_state == "PLAYING":
            checked_pairs = set()
            for current_cell_units in unit_grid.values():
                for u1 in current_cell_units:
                    if u1.is_performing or u1.stun_timer > 0 or u1.state == "DEAD": continue
                    
                    cx, cy = get_grid_key(u1.pos)
                    for dx in range(-1, 2):
                        for dy in range(-1, 2):
                            neighbor_key = (cx + dx, cy + dy)
                            if neighbor_key in unit_grid:
                                for u2 in unit_grid[neighbor_key]:
                                    if u1 == u2 or u2.is_performing or u2.stun_timer > 0 or u2.state == "DEAD": continue
                                    pair_id = (id(u1), id(u2)) if id(u1) < id(u2) else (id(u2), id(u1))
                                    if pair_id in checked_pairs: continue
                                    checked_pairs.add(pair_id)

                                    dist_sq = u1.pos.distance_squared_to(u2.pos)
                                    min_dist = u1.radius + u2.radius + 1 
                                    
                                    u1_reach_total = min_dist + u1.reach
                                    u2_reach_total = min_dist + u2.reach

                                    is_collided = dist_sq < min_dist * min_dist
                                    
                                    u1_is_attacking = u1.state in ("CHARGE", "STAY_ATTACK")
                                    u2_is_attacking = u2.state in ("CHARGE", "STAY_ATTACK")
                                    
                                    is_u1_weapon_hit = (u1_is_attacking and dist_sq <= (u1_reach_total) ** 2)
                                    is_u2_weapon_hit = (u2_is_attacking and dist_sq <= (u2_reach_total) ** 2)

                                    if is_collided or is_u1_weapon_hit or is_u2_weapon_hit:
                                        if is_collided:
                                            dist = math.sqrt(dist_sq) 
                                            push_dir = (u2.pos - u1.pos).normalize() if dist > 0 else pygame.math.Vector2(1, 0)
                                            overlap = min_dist - dist
                                            u1.pos -= push_dir * (overlap * 0.5)
                                            u2.pos += push_dir * (overlap * 0.5)

                                        if u1.team != u2.team:
                                            u1.attacker_memory = u2
                                            u2.attacker_memory = u1

                                            if u1_is_attacking and u1.cooldown_timer == 0:
                                                current_interval = u1.first_attack_delay if u1.is_first_attack else u1.attack_interval_max
                                                u1.cooldown_timer = current_interval + random.randint(-2, 2)
                                                u1.is_first_attack = False

                                                if u1.type == "cavalry":
                                                    u1.charge_hit_count += 1
                                                    current_spd = u1.vel.length()
                                                    if current_spd == 0: current_spd = 1.0
                                                    u2.hp -= (current_spd * 1.5 + u1.attack_power)
                                                    u1.current_thrust = max(u1.base_thrust, u1.current_thrust - 3.0)
                                                    if is_collided: u2.apply_force(push_dir * current_spd * 50.0) 
                                                    if u1.charge_hit_count >= 3:
                                                        u1.vel *= 0.1
                                                        u1.cooldown_timer = u1.attack_interval_max

                                                elif u1.type == "spearman":
                                                    is_tip_range = (min_dist + u1.reach * 0.3)**2 <= dist_sq <= (min_dist + u1.reach)**2
                                                    if is_tip_range and u2.type == "cavalry":
                                                        u2_id = id(u2)
                                                        if u2_id not in u1.hit_cavalry_ids:
                                                            u1.hit_cavalry_ids.add(u2_id)
                                                            u2.cavalry_stun_queue.append((12, 2.0)) 
                                                    
                                                    if u2.type == "melee_infantry":
                                                        s_dir = (u2.pos - u1.pos).normalize() if dist_sq > 0 else pygame.math.Vector2(1,0)
                                                        u2.apply_force(s_dir * 12.0)
                                                    u2.hp -= u1.attack_power

                                                elif u1.type == "melee_infantry":
                                                    u2_id = id(u2)
                                                    u1.consecutive_attack_counts[u2_id] = u1.consecutive_attack_counts.get(u2_id, 0) + 1
                                                    if u1.consecutive_attack_counts[u2_id] >= 10:
                                                        u2.hp -= 2
                                                        u1.attack_interval_max = 42
                                                    else:
                                                        u2.hp -= u1.attack_power
                                                        u1.attack_interval_max = 36  
                                                    if is_collided and u2.mass <= u1.mass:  
                                                        u2.apply_force(push_dir * 18.0)

                                            if u2_is_attacking and u2.cooldown_timer == 0:
                                                current_interval = u2.first_attack_delay if u2.is_first_attack else u2.attack_interval_max
                                                u2.cooldown_timer = current_interval + random.randint(-2, 2)
                                                u2.is_first_attack = False

                                                if u2.type == "cavalry":
                                                    u2.charge_hit_count += 1
                                                    current_spd = u2.vel.length()
                                                    if current_spd == 0: current_spd = 1.0
                                                    u1.hp -= (current_spd * 1.5 + u2.attack_power)
                                                    u2.current_thrust = max(u2.base_thrust, u2.current_thrust - 3.0)
                                                    if is_collided: u1.apply_force(-push_dir * current_spd * 50.0)
                                                    if u2.charge_hit_count >= 3:
                                                        u2.vel *= 0.1
                                                        u2.cooldown_timer = u2.attack_interval_max

                                                elif u2.type == "spearman":
                                                    is_tip_range = (min_dist + u2.reach * 0.3)**2 <= dist_sq <= (min_dist + u2.reach)**2
                                                    if is_tip_range and u1.type == "cavalry":
                                                        u1_id = id(u1)
                                                        if u1_id not in u2.hit_cavalry_ids:
                                                            u2.hit_cavalry_ids.add(u1_id)
                                                            u1.cavalry_stun_queue.append((12, 2.0)) 
                                                    
                                                    if u1.type == "melee_infantry":
                                                        s_dir = (u1.pos - u2.pos).normalize() if dist_sq > 0 else pygame.math.Vector2(-1,0)
                                                        u1.apply_force(s_dir * 12.0)
                                                    u1.hp -= u2.attack_power

                                                elif u2.type == "melee_infantry":
                                                    u1_id = id(u1)
                                                    u2.consecutive_attack_counts[u1_id] = u2.consecutive_attack_counts.get(u1_id, 0) + 1
                                                    if u2.consecutive_attack_counts[u1_id] >= 10:
                                                        u1.hp -= 2
                                                        u2.attack_interval_max = 42
                                                    else:
                                                        u1.hp -= u2.attack_power
                                                        u2.attack_interval_max = 36
                                                    if is_collided and u1.mass <= u2.mass:
                                                        u1.apply_force(-push_dir * 18.0)
                                    else:
                                        if is_collided:
                                            factor = 0.8 if (u1.state == "MOVE" or u2.state == "MOVE") else 1.2
                                            u1.apply_force(-push_dir * overlap * factor)
                                            u2.apply_force(push_dir * overlap * factor)

    # --- 画面描画 ---
        screen.fill((30, 30, 30))
        screen.blit(bg_image, (-int(camera_pos.x * zoom), -int(camera_pos.y * zoom)))

        # ─── 🏰 城（本部）のリアルタイム描画 ───
        scaled_w = int(CASTLE_SIZE[0] * zoom)
        scaled_h = int(CASTLE_SIZE[1] * zoom)
        
        cb_x = int((castle_blue_pos.x - camera_pos.x) * zoom) - scaled_w // 2
        cb_y = int((castle_blue_pos.y - camera_pos.y) * zoom) - scaled_h // 2
        castle_blue_surf = pygame.transform.scale(orig_castle_blue, (scaled_w, scaled_h))
        screen.blit(castle_blue_surf, (cb_x, cb_y))
        
        cr_x = int((castle_red_pos.x - camera_pos.x) * zoom) - scaled_w // 2
        cr_y = int((castle_red_pos.y - camera_pos.y) * zoom) - scaled_h // 2
        castle_red_surf = pygame.transform.scale(orig_castle_red, (scaled_w, scaled_h))
        screen.blit(castle_red_surf, (cr_x, cr_y))


        if game_state == "PLAYING" and selected_groups:
            for g_id in selected_groups:
                g_units = [u for u in friends if u.group_id == g_id]
                draw_formation_ui(screen, g_units, camera_pos, zoom)

        if game_state == "PLAYING" and is_aligning and selected_groups and current_active_mode == "FORMATION":
            g_center = get_groups_center(all_units, selected_groups)
            pygame.draw.line(screen, (255, 200, 0), 
                            (int((g_center.x - camera_pos.x) * zoom), int((g_center.y - camera_pos.y) * zoom)), 
                            (int((formation_center.x - camera_pos.x) * zoom), int((formation_center.y - camera_pos.y) * zoom)), 2) 
            if is_rotating:
                mouse_dist_sq = formation_center.distance_squared_to(world_mouse)
                if mouse_dist_sq > 25:
                    arrow_length = max(30, min(math.sqrt(mouse_dist_sq) * zoom, 120))
                    pygame.draw.line(screen, (255, 30, 30), 
                                    (int((formation_center.x - camera_pos.x) * zoom), int((formation_center.y - camera_pos.y) * zoom)), 
                                    (int((formation_center.x - camera_pos.x) * zoom) + int(arrow_length * math.cos(formation_angle)), int((formation_center.y - camera_pos.y) * zoom) + int(arrow_length * math.sin(formation_angle))), 4)
            for g_id in selected_groups:
                g_units = [u for u in friends if u.group_id == g_id]
                draw_formation_ui(screen, g_units, camera_pos, zoom, formation_center, formation_angle, 
                                is_preview=True, preview_stage=current_global_stage, preview_col_mode=current_global_col_mode)

        for u in all_units[:]:
            if game_state == "PLAYING":
                u.update(enemies if u.team == 0 else friends, current_target_counts)
            
            if u.hp <= 0 and u.state != "DEAD":
                u.state = "DEAD"
                u.attack_target = None
                u.vel *= 0
                
            if not u.alive:
                all_units.remove(u)  
            else:
                is_sel = u.group_id in selected_groups if game_state == "PLAYING" else False
                u.draw(screen, camera_pos, zoom, is_sel)

        if game_state == "PLAYING":
            reassign_timer += 1
            if reassign_timer >= 60:
                reassign_timer = 0
                if not is_aligning: 
                    active_groups = set(u.group_id for u in friends if u.state != "DEAD")
                    for g_id in active_groups:
                        if group_modes.get(g_id, "FORMATION") == "MELEE": continue  
                        g_units = [u for u in friends if u.group_id == g_id and u.state != "DEAD"]
                        if g_units:
                            if any(u.state == "MOVE" or u.commanded or u.is_performing for u in g_units): continue
                            if group_target_enemies.get(g_id, None) is not None: continue 
                            if all(u.pos.distance_squared_to(u.target) < 225 for u in g_units): continue
                            avg_t = pygame.math.Vector2(0, 0)
                            for u in g_units: avg_t += u.target
                            apply_formation_to_multiple_groups(all_units, {g_id}, avg_t / len(g_units), group_saved_angles.get(g_id, 0.0), clear_velocity=False)

            if is_dragging:
                pygame.draw.rect(screen, (0, 255, 255), (drag_start_pos[0], drag_start_pos[1], mx - drag_start_pos[0], my - drag_start_pos[1]), 2)

        # --- スタート画面用UIのオーバーレイ描画 ---
        if game_state == "START_MENU":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 60)) 
            screen.blit(overlay, (0, 0))
            
            font = pygame.font.SysFont("Arial", 44, bold=True)
            title_font = pygame.font.SysFont("Arial", 84, bold=True)
            
            title_surf = title_font.render("LEGION", True, (255, 100, 0))
            screen.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 130))
            
            start_y = 320
            for i, option in enumerate(menu_options):
                if i == selected_menu_idx:
                    text_color = (255, 230, 0)  
                    disp_text = f"> {option} <"
                else:
                    text_color = (255, 255, 255) 
                    disp_text = option
                    
                opt_surf = font.render(disp_text, True, text_color)
                screen.blit(opt_surf, (WIDTH // 2 - opt_surf.get_width() // 2, start_y + i * 75))

        draw_lockon_cursor(screen, mx, my, is_over_friend, is_over_enemy, current_active_mode)
        pygame.display.flip()
        clock.tick(FPS)

        await asyncio.sleep(0)
    
    pygame.quit()

asyncio.run(main())