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
        else:
            raise Exception(f"not a module: '{other_module}' ({type(other_module)})")
    def disconnect(self, input_name):
        self.inputs[input_name].connection = None
    def invoke(self, inputs, t):
        overall_inputs = {k:(inputs[k] if k in inputs else self.inputs[k].default) for k in self.inputs}
        outputs = self.f(t = t, **overall_inputs)
        for output, value in outputs.items():
            self.outputs[output].value = value
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
    def step(self, t):
        for module in self.modules:
            module.current_values = module.invoke({_input.name:_input.connection.value for _input in module.inputs.values() if _input.connection is not None}, t)
    def run(self, n, t = 0):
        # -1 to run unboundedly
        while n != 0:
            self.step(t)
            t += 1
            n -= 1



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
    def get_rect(self):
        return (20, 30 + (self.index*20), self.module.synth.smallfont.size(str(self.value))[0] + 20, 20)

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
        return (20, 30 + (self.index*20), self.module.synth.smallfont.size(str(self.name))[0] + 20, 20)

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
            return "drag bar"
        else:
            for widget in list(self.inputs.values()) + list(self.settings.values()) + list(self.outputs.values()):
                x,y,w,h = widget.get_rect()
                if (pos[0] > self.x + x and pos[0] < self.x + x + w and
                    pos[1] > self.y + y and pos[1] < self.y +y + h):
                    return widget
    def draw(self, screen):
        titlewidth = self.synth.font.size(self.name)[0] + 10
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
        pygame.draw.rect(surface, (50,50,50), pygame.Rect(0, 0, width, titleheight))
        title = self.synth.font.render(self.name, True, (250,250,250))
        surface.blit(title, (5, 5))
        for _input in self.inputs.values():
            _input.draw(surface)
        for output in self.outputs.values():
            output.draw(surface)
        for setting in self.settings.values():
            setting.draw(surface)
        if self.visualiser is not None:
            self.visualiser.draw(surface)
        screen.blit(surface, (self.x, self.y))
            
        

class VisualSynth(Synth):
    def __init__(self, rate = 10):
        super().__init__(rate = rate)
        self.font = pygame.font.Font(None, 24)
        self.smallfont = pygame.font.Font(None, 18)
        self.dragging = None
        self.connecting = None
        self.menu_open = None
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
            if mouseevent.type == pygame.MOUSEBUTTONDOWN:
                module_found = False
                for module in self.modules:
                    if (mouseevent.pos[0] > module.x and mouseevent.pos[0] < module.x + module.w and
                        mouseevent.pos[1] > module.y and mouseevent.pos[1] < module.y + module.h):
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
                        module_found = True
                        break
                if not module_found:
                    self.connecting = None

                                                
        

def window(synth, framerate):
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    running = True
    t = 0
    while running:
        # do the right amount of iterations to have the specified synth sample rate. rounding errors are possible, which may matter for audio
        synth.run(math.ceil(synth.rate / framerate), t = t)
        t += math.ceil(synth.rate / framerate)

        # poll for events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type in [pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]:
                synth.mouse(event)

        screen.blit(synth.render(screen.get_size()), (0,0))

        # flip() the display to put your work on screen
        pygame.display.flip()

        clock.tick(framerate)
    pygame.quit()


## TESTING

# test modules
class Osc(VisualModule):
    name = "Osc"
    inputs = {"frequency": (float, 1.)}
    outputs = {"out": float}
    settings = {"waveform": ("enum", ["sin", "tri", "saw", "squ"], 0)}
    def f(self, t, frequency):
        return {"out": {"sin": math.sin,
                        "tri": lambda x: abs((((2*x)/math.pi)%4)-2)-1,
                        "saw": lambda x: (abs(x/math.pi)%2)-1,
                        "squ": lambda x: 1 if (x%(math.pi*2)) < math.pi else -1}[self.settings["waveform"].value](t*frequency)}

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
class VideoOut(VisualModule):
    global sweeps
    name = "--------------- Video Output ---------------"
    inputs = {"r": (float, 0.), "g": (float, 0.), "b": (float, 0.)}
    settings = {"path": ("enum", ["horizontal", "vertical"], 0),
                "pixel size": ("enum", [1,2,3,4], 0)}
    visualiser = ("output", (1,1), videoout_f)
    pointer = (0,0)
    def __init__(self, synth):
        super().__init__(synth)
        _,_,w,h = self.visualiser.get_rect()
        self.screenbuffer = pygame.Surface((w,h))
    def f(self, t, r, g, b):
        pixelsize = self.settings["pixel size"].value
        x,y = self.pointer
        _,_,w,h = self.visualiser.get_rect()
        buffer_w, buffer_h = self.screenbuffer.get_size()
        if buffer_w != w or buffer_h != h:
            self.screenbuffer = pygame.Surface((w,h))
        if self.settings["path"].value == "horizontal":
            x = int((x + 1) % math.ceil(w/pixelsize)) if w > 0 else 0
            if x == 0:
                y = int((y + 1) % math.ceil(h/pixelsize)) if h > 0 else 0
        elif self.settings["path"].value == "vertical":
            y = int((y + 1) % h) if h > 0 else 0
            if y == 0:
                x = int((x + 1) % w) if w > 0 else 0
        self.pointer = (x,y)
        pygame.draw.rect(self.screenbuffer, (127+int(r*127),127+int(g*127),127+int(b*127)),
                         (x*pixelsize, y*pixelsize, pixelsize, pixelsize))
        return {}

def resetscreenbuffer(module):
    _,_,w,h = module.visualiser.get_rect()
    module.screenbuffer = pygame.Surface((w,h))
class SteeredVideoOut(VisualModule):
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
    outputs = {"x": (float, 0.), "y": (float, 0.)}
    settings = {"resolution": ("enum", [100,200, 300],0),
                "mode": ("enum", ["vertical", "horizontal", "boustro (h)", "boustro (v)", "spiral"], 0)}
    pointer = (0,0)
    def f(self, t):
        x,y = self.pointer
        res = self.settings["resolution"].value
        mode = self.settings["mode"].value
        if mode == "horizontal":
            x = int((x + 1) % res)
            if x == 0:
                y = int((y + 1) % res)
        elif mode == "vertical":
            y = int((y + 1) % res)
            if y == 0:
                x = int((x + 1) % res)
        elif mode == "boustro (h)":
            x = int((x + (1 if y % 2 == 0 else -1)) % res)
            if x == 0:
                y = int((y + 1) % res)
        elif mode == "boustro (v)":
            y = int((y + (1 if x % 2 == 0 else -1)) % res)
            if y == 0:
                x = int((x + 1) % res)
        self.pointer = (x,y)
        return {"x": (x/(res/2))-1, "y": (y/(res/2))-1}

class Magnitude(VisualModule):
    name = "Magnitude"
    outputs = {"out": (float, 0.)}
    settings = {"value": ("enum", [0.0001, 0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000], 4)}
    def f(self, t):
        return {"out": self.settings["value"].value}

synth = VisualSynth(rate = 100000)
osc_a = synth.create_module(Osc)
osc_b = synth.create_module(Osc)
osc_b.x = 100
vis = synth.create_module(SteeredVideoOut)
vis.x = 300
mag = synth.create_module(Magnitude)
mag.x = 400
pat = synth.create_module(PathGen)
pat.y = 100
window(synth, 30)





