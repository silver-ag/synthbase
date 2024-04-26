import math
import pygame

# MODULE SYSTEM

class Input:
    def __init__(self, module, name, _type, default):
        self.module = module
        self.name = name
        self.type = _type
        self.default = default
        self.connection = None # where is this reading from - an Output
        if not isinstance(self.default, self.type):
            raise Exception(f"default value '{default}' is not of declared type ({_type})")

class Output:
    def __init__(self, module, name, _type):
        self.module = module
        self.name = name
        self.type = _type
        self.value = None
        self.connections = set() # we need to be able to follow connections both ways to extricate deleted modules

class Setting:
    def __init__(self, module, name, default):
        self.module = module
        self.name = name
        self.default = default
        self.value = default
        if not isinstance(self.default, self.type):
            raise Exception(f"default value '{default}' is not of declared type ({_type})")

class Module:
    inputs = {}
    outputs = {}
    settings = {}
    current_values = {}
    name = "[module]"
    error = None
    def __init__(self, synth):
        self.synth = synth
        self.gen_widgets()
    def gen_widgets(self):
        self.inputs = {name: Input(self, name, _type, default) for name,(_type,default) in self.inputs.items()}
        self.outputs = {name: Output(self, name, _type) for name,_type in self.outputs.items()}
        self.settings = {name: Setting(self, name, _type, default) for name,(_type,default) in self.settings.items()}
    def connect_from(self, input_name, other_module, output_name):
        if isinstance(other_module, Module):
            self.inputs[input_name].connection = other_module.outputs[output_name]
            other_module.outputs[output_name].connections.add(self.inputs[input_name])
        else:
            raise Exception(f"not a module: '{other_module}' ({type(other_module)})")
    def disconnect(self, input_name):
        if self.inputs[input_name].connection is not None:
            self.inputs[input_name].connection.connections.remove(self.inputs[input_name])
            self.inputs[input_name].connection = None
    def invoke(self, inputs, t):
        overall_inputs = {k:(inputs[k] if k in inputs else self.inputs[k].default) for k in self.inputs}
        self.error = None
        try:
            outputs = self.f(t = t, **overall_inputs)
        except Exception as e:
            self.error = e
            outputs = {}
        for output, value in outputs.items():
            self.outputs[output].value = value
    def destroy(self):
        for output in self.outputs.values():
            for connection in set(output.connections): # need to copy output.connections so we don't alter its size while iterating over it
                connection.module.disconnect(connection.name)
    def setting_changed(self):
        pass # for settings to signal when they've been changed, in case we need to do something about that like only processing them after they're changed for performance reasons
    def f(self, t, **inputs):
        print("Module.f must be shadowed with a function that does the operations of the module, taking named arguments for all the inputs plus a time t and returning a dict of output values")

class Synth:
    modules = set()
    def __init__(self, rate = 10):
        self.rate = rate
    def create_module(self, module):
        m = module(self)
        self.modules.add(m)
        return m
    def remove_module(self, module):
        if module in self.modules:
            self.modules.remove(module)
            module.destroy()
    def step(self, t):
        for module in self.modules:
            module.current_values = module.invoke({_input.name:_input.connection.value for _input in module.inputs.values() if _input.connection is not None}, t)
    def run(self, n, t_from, t_to):
        for i in range(n):
            self.step(t_from + ((t_to/n)*i))


class RepeatCounter:
    # object to handle figuring out how many times to do something each tick to achieve a particular rate in hz
    # always returns 0 on the first call, so it doesn't try to do as many repeats as needed since the system was started
    # this is because we don't know the value of t during instantiation
    def __init__(self, rate):
        self.rate = rate # in hz
        self.t_last_repeat = 0
    def repeats(self, t):
        self.t_last_repeat = t
        self.repeats = self.real_repeats
        return 0
    def real_repeats(self, t):
        if self.rate > 0:
            delta_t = t - self.t_last_repeat
            repetitions = int(delta_t * self.rate)
            self.t_last_repeat += (repetitions/self.rate)
            return repetitions
        else:
            return 0


# VISUAL INTERFACE

pygame.init()

class VisualInput(Input):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index = self.module.make_index('input')
    def draw(self, surface):
        x,y,w,h = self.get_rect()
        pygame.draw.circle(surface, (100,200,100), (x + (w/2), y + (h/2)), min(w,h)*0.4, 3)
    def get_rect(self):
        return (0, 30 + (self.index * 20), 20, 20)

class VisualOutput(Output):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index = self.module.make_index('output')
    def draw(self, surface):
        x,y,w,h = self.get_rect()
        pygame.draw.circle(surface, (200,100,100), (x + (w/2), y + (h/2)), min(w,h)*0.4, 3)
    def get_rect(self):
        return (self.module.w - 20, 30 + (self.index * 20), 20, 20)

class VisualEnumSetting(Setting):
    def __init__(self, module, name, options, default_choice):
        self.module = module
        self.index = self.module.make_index('setting')
        self.name = name
        self.options = options
        self.default_choice = default_choice
        self.choice = default_choice
    @property
    def value(self):
        return self.options[self.choice]
    def draw(self, surface):
        x,y,w,h = self.get_rect()
        pygame.draw.rect(surface, (70,70,70), pygame.Rect(x, y+2, w, h-4))
        value_text = self.module.synth.smallfont.render(str(self.value), True, (250,250,250))
        surface.blit(value_text, (x+5,y+4))
    def draw_menu(self, surface):
        x,y,w,h = self.get_rect()
        x += self.module.x
        y += self.module.y
        pygame.draw.rect(surface, (70, 70, 70), pygame.Rect(x-2, y, w+4, h * len(self.options)))
        for i in range(len(self.options)):
            pygame.draw.rect(surface, (100,100,100), pygame.Rect(x, (20*i) + y+2, w, h-4))
            value_text = self.module.synth.smallfont.render(str(self.options[i]), True, (250,250,250))
            surface.blit(value_text, (x + 5, (20*i) + y + 4))
    def menu_click(self, pos):
        x,y,w,h = self.get_rect()
        x += self.module.x
        y += self.module.y
        if pos[0] > x and pos[0] < x + w:
            index = int((pos[1] - y)/20)
            if index >=0 and index < len(self.options):
                self.choice = index
                self.module.setting_changed()
    def get_rect(self):
        return (max([_input.get_rect()[2] for _input in self.module.inputs.values()] + [0]),
                30 + (self.index*20), self.module.synth.smallfont.size(str(self.value))[0] + 20, 20)

class VisualTextSetting(Setting):
    def __init__(self, module, name, default):
        self.module = module
        self.index = self.module.make_index('setting')
        self.name = name
        self.value = default
        self.cursor = 0
        self.is_selected = False
    def draw(self, surface):
        x,y,w,h = self.get_rect()
        pygame.draw.rect(surface, (70,70,70), pygame.Rect(x, y+2, w, h-4))
        value_text = self.module.synth.smallfont.render(str(self.value), True, (250,250,250))
        surface.blit(value_text, (x+5,y+4))
        if self.is_selected:
            cursor_x = self.module.synth.smallfont.size(self.value[:self.cursor])[0]
            pygame.draw.line(surface, (250,250,250), (cursor_x + x + 5, y + 3), (cursor_x + x + 5, y + h - 3))
    def keypress(self, keyevent):
        if keyevent.key == pygame.K_LEFT:
            if self.cursor > 0:
                self.cursor -= 1
        elif keyevent.key == pygame.K_RIGHT:
            if self.cursor < len(self.value):
                self.cursor += 1
        elif keyevent.key == pygame.K_BACKSPACE:
            self.value = self.value[:self.cursor-1] + self.value[self.cursor:]
            if self.cursor > 0:
                self.cursor -= 1
        elif keyevent.key == pygame.K_DELETE:
            self.value = self.value[:self.cursor] + self.value[self.cursor+1:]
        else:
            self.value = self.value[:self.cursor] + keyevent.unicode + self.value[self.cursor:]
            self.cursor += len(keyevent.unicode)
        self.module.setting_changed()
    def selected(self):
        self.is_selected = True
        self.cursor = len(self.value)
    def deselected(self):
        self.is_selected = False
    def get_rect(self):
        return (max([_input.get_rect()[2] for _input in self.module.inputs.values()] + [0]),
                30 + (self.index*20), self.module.synth.smallfont.size(str(self.value))[0] + 20, 20)

class VisualTriggerSetting:
    def __init__(self, module, name, action):
        self.module = module
        self.name = name
        self.action = action
        self.index = self.module.make_index('setting')
    def click(self):
        self.action(self.module)
    def draw(self, surface):
        x,y,w,h = self.get_rect()
        pygame.draw.rect(surface, (70,70,70), pygame.Rect(x, y+2, w, h-4))
        value_text = self.module.synth.smallfont.render(str(self.name), True, (250,250,250))
        surface.blit(value_text, (x+5,y+4))
    def get_rect(self):
        return (max([_input.get_rect()[2] for _input in self.module.inputs.values()] + [0]),
                30 + (self.index*20), self.module.synth.smallfont.size(str(self.name))[0] + 20, 20)

class Visualiser:
    def __init__(self, module, name, aspect_ratio, f):
        self.module = module
        self.index = self.module.make_index('visualiser')
        self.name = name
        self.aspect_ratio = aspect_ratio
        self.f = f
    def draw(self, surface):
        x,y,w,h = self.get_rect()
        overall_inputs = {k:self.module.inputs[k].connection.value
                          if (self.module.inputs[k].connection is not None and
                              self.module.inputs[k].connection.value is not None)
                          else self.module.inputs[k].default for k in self.module.inputs}
        surface.blit(self.f(pygame.Surface((w,h)), overall_inputs, self.module.current_values, self.module),
                     (x,y))
    def get_rect(self):
        return (0,
                self.module.titleheight +
                max(sum([_input.get_rect()[3] for _input in self.module.inputs.values()]),
                    sum([output.get_rect()[3] for output in self.module.outputs.values()])),
                self.module.w, (self.module.w/self.aspect_ratio[0])*self.aspect_ratio[1])

class VisualModule(Module):
    x = 0
    y = 0
    w = 0
    h = 0
    titleheight = 30
    visualiser = None # (name, aspect_ratio, f)
    def gen_widgets(self):
        self.indices = {}
        self.inputs = {name: VisualInput(self, name, _type, default) for name,(_type,default) in self.inputs.items()}
        self.outputs = {name: VisualOutput(self, name, _type) for name,_type in self.outputs.items()}
        new_settings = {}
        for name,config in self.settings.items():
           if config[0] == "enum":
               new_settings[name] = VisualEnumSetting(self, name, config[1], config[2])
           elif config[0] == "trig":
               new_settings[name] = VisualTriggerSetting(self, name, config[1])
           elif config[0] == "text":
               new_settings[name] = VisualTextSetting(self, name, config[1])
        self.settings = new_settings
        self.visualiser = Visualiser(self, self.visualiser[0], self.visualiser[1], self.visualiser[2]) if self.visualiser is not None else None
    def make_index(self, kind):
        if kind in self.indices:
            self.indices[kind] += 1
        else:
            self.indices[kind] = 0
        return self.indices[kind]
    def mouse_click(self, pos):
        if pos[1] < self.y + self.titleheight:
            if pos[0] > self.x + self.w - 20:
                self.synth.remove_module(self)
                return "module closed"
            return "drag bar"
        else:
            for widget in list(self.inputs.values()) + list(self.settings.values()) + list(self.outputs.values()):
                x,y,w,h = widget.get_rect()
                if (pos[0] > self.x + x and pos[0] < self.x + x + w and
                    pos[1] > self.y + y and pos[1] < self.y +y + h):
                    return widget
    def draw(self, screen):
        titlewidth = self.synth.font.size(self.name)[0] + 10 + 20
        titleheight = 30
        height = (titleheight +
                  max(sum([_input.get_rect()[3] for _input in self.inputs.values()]),
                      sum([setting.get_rect()[3] for setting in self.settings.values()]),
                      sum([output.get_rect()[3] for output in self.outputs.values()])) +
                  (self.visualiser.get_rect()[3] if self.visualiser is not None else 0))
        width = max(titlewidth, max([_input.get_rect()[2] for _input in self.inputs.values()] + [0]) +
                                max([setting.get_rect()[2] for setting in self.settings.values()] + [0]) +
                                max([output.get_rect()[2] for output in self.outputs.values()] + [0]))
        self.h = height
        self.w = width
        surface = pygame.Surface((width, height))
        surface.fill((100,100,100))
        if self.error is None:
            pygame.draw.rect(surface, (50,50,50), pygame.Rect(0, 0, width, titleheight))
            title = self.synth.font.render(self.name, True, (250,250,250))
        else:
            pygame.draw.rect(surface, (100, 50, 50), pygame.Rect(0,0,width,titleheight))
            title = self.synth.smallfont.render(str(self.error), True, (250,250,250))
        surface.blit(title, (5, 5))
        pygame.draw.line(surface, (250, 250, 250), (width - 18, 2), (width - 2, 18))
        pygame.draw.line(surface, (250, 250, 250), (width - 2, 2), (width - 18, 18))
        for _input in self.inputs.values():
            _input.draw(surface)
        for output in self.outputs.values():
            output.draw(surface)
        for setting in self.settings.values():
            setting.draw(surface)
        if self.visualiser is not None:
            self.visualiser.draw(surface)
        screen.blit(surface, (self.x, self.y))
            
        

class RightClickMenu:
    location = (0,0)
    def __init__(self, synth, library):
        self.synth = synth
        self.library = library
        self.width = max([synth.smallfont.size(module.name)[0] for module in library]) + 10
        self.height = 20 * len(library)
    def draw_menu(self, surface):
        x,y = self.location
        pygame.draw.rect(surface, (70, 70, 70), pygame.Rect(x, y, self.width, self.height + 10))
        for i in range(len(self.library)):
            pygame.draw.rect(surface, (100,100,100), pygame.Rect(x+5, (20*i) + y + 5, self.width - 10, 18))
            value_text = self.synth.smallfont.render(self.library[i].name, True, (250,250,250))
            surface.blit(value_text, (x + 5, (20*i) + y + 8))
    def menu_click(self, pos):
        if pos[0] > self.location[0] and pos[0] < self.location[0] + self.width:
            index = int((pos[1] - (self.location[1] + 5))/20)
            if index >=0 and index < len(self.library):
                self.synth.create_module(self.library[index], location = self.location)

class VisualSynth(Synth):
    def __init__(self, library, rate = 10):
        super().__init__(rate = rate)
        self.font = pygame.font.Font(None, 24)
        self.smallfont = pygame.font.Font(None, 18)
        self.dragging = None
        self.connecting = None
        self.menu_open = None
        self.text_selection = None
        self.tooltip_open = None
        self.right_click_menu = RightClickMenu(self, library)
    def create_module(self, module, location = (0,0)):
        module = super().create_module(module)
        module.x = location[0]
        module.y = location[1]        
    def render(self, size):
        surface = pygame.Surface(size)
        surface.fill("purple")
        for module in self.modules:
            module.draw(surface)
        for module in self.modules:
            for _input in module.inputs.values():
                if _input.connection:
                    xa,ya,wa,ha = _input.get_rect()
                    xb,yb,wb,hb = _input.connection.get_rect()
                    xa += _input.module.x
                    ya += _input.module.y
                    xb += _input.connection.module.x
                    yb += _input.connection.module.y
                    pygame.draw.line(surface, (200,200,200), (xa + (wa/2), ya + (ha/2)), (xb + (wb/2), yb + (hb/2)), width = 3)
        if self.connecting:
            x,y,w,h = self.connecting.get_rect()
            x += self.connecting.module.x
            y += self.connecting.module.y
            mx,my = pygame.mouse.get_pos()
            pygame.draw.line(surface, (200,200,200), (x + (w/2), y + (h/2)), (mx, my))
        if self.tooltip_open is not None:
            x,y,w,h = self.tooltip_open.get_rect()
            x += self.tooltip_open.module.x + (w/2)
            y += self.tooltip_open.module.y + (h/2)
            w,h = self.smallfont.size(self.tooltip_open.name)
            pygame.draw.rect(surface, (170,170,170), pygame.Rect(x,y,w+10, h+10))
            text = self.smallfont.render(self.tooltip_open.name, True, (0,0,0))
            surface.blit(text, (x + 5, y + 5))
        if self.menu_open is not None:
            self.menu_open.draw_menu(surface)
        return surface
    def mouse(self, mouseevent):
        if self.dragging:
            if mouseevent.type == pygame.MOUSEMOTION:
                self.dragging.x += mouseevent.rel[0]
                self.dragging.y += mouseevent.rel[1]
            elif mouseevent.type == pygame.MOUSEBUTTONUP:
                self.dragging = None
        elif self.menu_open:
            if mouseevent.type == pygame.MOUSEBUTTONDOWN:
                self.menu_open.menu_click(mouseevent.pos)
                self.menu_open = None
        else: 
            module_found = None
            for module in self.modules:
                if (mouseevent.pos[0] > module.x and mouseevent.pos[0] < module.x + module.w and
                    mouseevent.pos[1] > module.y and mouseevent.pos[1] < module.y + module.h):
                    module_found = module
                    break
            if mouseevent.type == pygame.MOUSEBUTTONDOWN:
                if self.text_selection is not None:
                    self.text_selection.deselected()
                self.text_selection = None

                if mouseevent.button == 3: # right click
                    self.menu_open = self.right_click_menu
                    self.menu_open.location = mouseevent.pos

                if module_found is not None:
                    clicked_on = module.mouse_click(mouseevent.pos)
                    if clicked_on == 'drag bar':
                        self.dragging = module
                    elif isinstance(clicked_on, VisualInput):
                        if self.connecting:
                            if isinstance(self.connecting, VisualOutput):
                                if clicked_on.connection == self.connecting:
                                    clicked_on.module.disconnect(clicked_on.name)
                                else:
                                    clicked_on.module.connect_from(clicked_on.name, self.connecting.module, self.connecting.name)
                            self.connecting = None
                        else:
                            self.connecting = clicked_on
                    elif isinstance(clicked_on, VisualOutput):
                        if self.connecting:
                            if isinstance(self.connecting, VisualInput):
                                if self.connecting.connection == clicked_on:
                                    self.connecting.module.disconnect(self.connecting.name)
                                else:
                                    self.connecting.module.connect_from(self.connecting.name, clicked_on.module, clicked_on.name)
                            self.connecting = None
                        else:
                            self.connecting = clicked_on
                    elif isinstance(clicked_on, VisualEnumSetting):
                        if not self.connecting:
                            self.menu_open = clicked_on
                    elif isinstance(clicked_on, VisualTriggerSetting):
                        if not self.connecting:
                            clicked_on.click()
                    elif isinstance(clicked_on, VisualTextSetting):
                        if self.text_selection is not None:
                            self.text_selection.deselected()
                        self.text_selection = clicked_on
                        self.text_selection.selected()
                else:
                    self.connecting = None
            elif mouseevent.type == pygame.MOUSEMOTION:
                if module_found:
                    self.tooltip_open = None
                    for widget in list(module_found.inputs.values()) + list(module_found.settings.values()) + list(module_found.outputs.values()):
                        x,y,w,h = widget.get_rect()
                        if (mouseevent.pos[0] > module.x + x and mouseevent.pos[0] < module.x + x + w and
                            mouseevent.pos[1] > module.y + y and mouseevent.pos[1] < module.y + y + h):
                            self.tooltip_open = widget
                else:
                    self.tooltip_open = None
    def key(self, keyevent):
        if self.text_selection is not None:
            self.text_selection.keypress(keyevent)


def window(synth, framerate):
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    running = True
    t = 0
    repeat_counter = RepeatCounter(synth.rate)
    while running:
        # do the right amount of iterations to have the specified synth sample rate. rounding errors are possible, which may matter for audio
        synth.run(repeat_counter.repeats(t), t, 1/framerate)
        t += 1/framerate

        # poll for events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type in [pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]:
                synth.mouse(event)
            if event.type == pygame.KEYDOWN:
                synth.key(event)

        screen.blit(synth.render(screen.get_size()), (0,0))

        # flip() the display to put your work on screen
        pygame.display.flip()

        clock.tick(framerate)
    pygame.quit()


## TESTING

# test modules
class Osc(VisualModule):
    name = "Osc"
    inputs = {"frequency": (float, 1.), "phase": (float, 0.)}
    outputs = {"out": float}
    settings = {"waveform": ("enum", ["sin", "tri", "saw", "squ"], 0)}
    def f(self, t, frequency, phase):
        return {"out": {"sin": lambda x: math.sin(2 * math.pi * x),
                        "tri": lambda x: abs(((4*x)%4)-2)-1,
                        "saw": lambda x: (abs(2*x)%2)-1,
                        "squ": lambda x: 1 if (x%1) < 0.5 else -1}[self.settings["waveform"].value]((t + phase)*frequency)}

def lightvis_f(surface, inputs, outputs, module):
    surface.fill((127+int(inputs['value']*127),0,0))
    return surface
class LightVis(VisualModule):
    name = "Light Visualiser"
    inputs = {"value": (float, 0.)}
    visualiser = ("lightvis", (2,1), lightvis_f)
    def f(self, t, value):
        return {}

def videoout_f(surface, inputs, outputs, module):
    return module.screenbuffer
def resetscreenbuffer(module):
    _,_,w,h = module.visualiser.get_rect()
    module.screenbuffer = pygame.Surface((w,h))
class VideoOut(VisualModule):
    name = "--------------- Video Output ---------------"
    inputs = {"x": (float, 0.), "y": (float, 0.), "r": (float, 0.), "g": (float, 0.), "b": (float, 0.)}
    settings = {"pixel size": ("enum", [1,2,3,4], 0),
                "reset": ("trig", resetscreenbuffer)}
    visualiser = ("output", (1,1), videoout_f)
    def __init__(self, synth):
        super().__init__(synth)
        _,_,w,h = self.visualiser.get_rect()
        self.screenbuffer = pygame.Surface((w,h))
    def f(self, t, x, y, r, g, b):
        pixelsize = self.settings["pixel size"].value
        _,_,w,h = self.visualiser.get_rect()
        buffer_w, buffer_h = self.screenbuffer.get_size()
        if buffer_w != w or buffer_h != h:
            self.screenbuffer = pygame.Surface((w,h))
        pygame.draw.rect(self.screenbuffer, ((127+int(r*127))%256,(127+int(g*127))%256,(127+int(b*127))%256),
                         (int((x+1)*buffer_w*0.5*(1/pixelsize))*pixelsize, int((y+1)*buffer_h*0.5*(1/pixelsize))*pixelsize, pixelsize, pixelsize))
        return {}

class PathGen(VisualModule):
    name = "Path Generator"
    outputs = {"x": float, "y": float}
    settings = {"resolution": ("text", "300"),
                "speed": ("text", "1"),
                "mode": ("enum", ["vertical", "horizontal", "boustro (v)", "boustro (h)", "spiral"], 0),
                "direction": ("enum", ["forwards", "reverse"], 0)}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repeat_counter = RepeatCounter(int(self.settings["speed"].value))
        self.gen_path()
    def f(self, t):
        try:
            res = int(self.settings["resolution"].value)
            1/res # to make sure res isn't 0
        except:
            res = 1
        speed = float(self.settings["speed"].value)
        index = min(math.floor(((t%(1/speed))/(1/speed))*len(self.path)), len(self.path)-1)
        x,y = self.path[index if self.settings["direction"].value == "forwards" else (len(self.path)-index)]
        return {"x": (x/(res/2))-1, "y": (y/(res/2))-1}
    def setting_changed(self):
        try:
            self.repeat_counter.rate = int(self.settings["speed"].value)
        except:
            pass
        self.gen_path()
    def gen_path(self):
        try:
            res = int(self.settings["resolution"].value)
            1/res # to make sure res isn't 0
        except:
            res = 1
        mode = self.settings["mode"].value
        self.path = []
        if mode == "vertical":
            for y in range(0, res):
                for x in range(0, res):
                    self.path.append((x,y))
        elif mode == "horizontal":
            for x in range(0, res):
                for y in range(0, res):
                    self.path.append((x,y))
        elif mode == "boustro (v)":
            for y in range(0, res):
                for x in range(0, res):
                    if y % 2 == 0:
                        self.path.append((x,y))
                    else:
                        self.path.append(((res-1)-x, y))
        elif mode == "boustro (h)":
            for x in range(0, res):
                for y in range(0, res):
                    if x % 2 == 0:
                        self.path.append((x,y))
                    else:
                        self.path.append((x, (res-1)-y))
        elif mode == "spiral":
            for sidelen in range(res, 0, -2):
                margin = (res-sidelen)/2
                self.path += [(margin + x, margin) for x in range(0, sidelen)]
                self.path += [(margin + sidelen, margin + y) for y in range(0, sidelen)]
                self.path += [(margin + sidelen - x, margin + sidelen) for x in range(0, sidelen)]
                self.path += [(margin, margin + sidelen - y) for y in range(0, sidelen)]
            self.path.append((res/2,res/2))

class Constant(VisualModule):
    name = "Constant"
    outputs = {"value": float}
    settings = {"value": ("text", "0")}
    def f(self, t):
        try:
            return {"value": float(self.settings["value"].value)}
        except:
            return {"value": 0.}

class Add(VisualModule):
    name = "Add"
    inputs = {"a": (float, 0.), "b": (float, 0.)}
    outputs = {"sum": float}
    def f(self, t, a, b):
        return {"sum": a + b}

class Multiply(VisualModule):
    name = "Multiply"
    inputs = {"a": (float, 1.), "b": (float, 1.)}
    outputs = {"product": float}
    def f(self, t, a, b):
        return {"product": a * b}

class EvalExpr(VisualModule):
    name = "Expression"
    inputs = {"x": (float, 0.), "y": (float, 0.), "z": (float, 0.)}
    outputs = {"value": float}
    settings = {"expression": ("text", "x + y + z")}
    compiled_expression = compile("x + y + z", "<user-defined expression>", "eval")
    def f(self, t, x, y, z):
        try:
            return {"value": eval(self.compiled_expression, {"x": x, "y": y, "z": z, "math": math})}
        except:
            return {"value": 0.}
    def setting_changed(self):
        try:
            self.compiled_expression = compile(self.settings["expression"].value, "<user-defined expression>", "eval")
        except:
            pass
        

class Threshold(VisualModule):
    name = "Threshold"
    inputs = {"value": (float, 0.), "threshold": (float, 0.)}
    outputs = {"gate": bool}
    def f(self, t, value, threshold):
        return {"gate": value > threshold}

class Choice(VisualModule):
    name = "Choice"
    inputs = {"gate": (bool, True), "a": (float, 0.), "b": (float, 0.)}
    outputs = {"out": float}
    def f(self, t, gate, a, b):
        return {"out": a if gate else b}

def adsr_trigger(module):
    module.manually_triggered = True
class ADSR(VisualModule):
    name = "ADSR"
    inputs = {"gate": (bool, False)}
    outputs = {"envelope": float}
    settings = {"attack": ("text", "0.25"), "decay": ("text", "0.25"), "sustain": ("text", "0.25"), "release": ("text", "0.25"),
                "trigger": ("trig", adsr_trigger)}
    prev_gate = False
    trigger_time = 0
    manually_triggered = False
    def f(self, t, gate):
        if (gate == True and self.prev_gate == False) or self.manually_triggered:
            self.trigger_time = t
            self.manually_triggered = False
        self.prev_gate = gate
        try:
            a,d,s,r = (float(self.settings["attack"].value), float(self.settings["decay"].value),
                       float(self.settings["sustain"].value), float(self.settings["release"].value))
        except:
            return {"envelope": 0}
        progress = t - self.trigger_time
        if progress < a:
            v = progress/a
        elif progress < a+d:
            v = 1 - (0.5*((progress - a)/d))
        elif progress < a+d+s:
            v = 0.5
        elif progress < a+d+s+r:
            v = 0.5 - (0.5*((progress - (a+d+s))/r))
        else:
            v = 0
        return {"envelope": v}

def image_visualiser(surface, inputs, outputs, module):
    _,_,w,h = module.visualiser.get_rect()
    return pygame.transform.scale(module.image, (w,h))
class ImageIn(VisualModule):
    name = "Image Input"
    inputs = {"x": (float, 0.), "y": (float, 0.)}
    outputs = {"r": float, "g": float, "b": float}
    settings = {"filename": ("text", "<filename>")}
    visualiser = ("image", (100,100), image_visualiser)
    image = None
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image = pygame.Surface((1,1))
    def f(self, t, x, y):
        w,h = self.image.get_size()
        r,g,b,_ = self.image.get_at((min(math.floor(((x/2)+0.5)*w), w-1), min(math.floor(((y/2)+0.5)*h), h-1)))
        r = ((r/255)*2)-1
        g = ((g/255)*2)-1
        b = ((b/255)*2)-1
        return {"r": r, "g": g, "b": b}
    def setting_changed(self):
        try:
            self.image = pygame.image.load(self.settings["filename"].value)
            self.visualiser.aspect_ratio = self.image.get_size()
        except:
            self.image = pygame.Surface((1,1))
        
        
            

synth = VisualSynth(library = [Osc, Constant, Add, Multiply, EvalExpr, Threshold, Choice, ADSR, PathGen, VideoOut, ImageIn], rate = 100000)
window(synth, 30)





