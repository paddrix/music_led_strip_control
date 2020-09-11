import numpy as np
from scipy.ndimage.filters import gaussian_filter1d

class ColorService():
    def __init__(self, config):

        self._config = config
        self.full_gradients = {}
        self.full_fadegradients = {}
        self.full_slide = {}
        self.full_bubble = {}

    def build_gradients(self):

        self.full_gradients = {}

        for gradient in self._config["gradients"]:
            not_mirrored_gradient = self._easing_gradient_generator(
                self._config["gradients"][gradient], # All colors of the current gradient
                self._config["device_config"]["LED_Count"]
            )

            # Mirror the gradient to get seemsles transition from start to the end
            # [1,2,3,4]
            # -> [1,2,3,4,4,3,2,1]
            self.full_gradients[gradient] = np.concatenate(
                (not_mirrored_gradient[:, ::-1], not_mirrored_gradient), 
                axis = 1
                )

    def build_fadegradients(self):

        self.full_fadegradients = {}

        for gradient in self._config["gradients"]:
            not_mirrored_gradient = self._easing_gradient_generator(
                self._config["gradients"][gradient], # All colors of the current gradient
                2000
            )

            # Mirror the gradient to get seemsles transition from start to the end
            # [1,2,3,4]
            # -> [1,2,3,4,4,3,2,1]
            self.full_fadegradients[gradient] = np.concatenate(
                (not_mirrored_gradient[:, ::-1], not_mirrored_gradient), 
                axis = 1
                )

    def _easing_gradient_generator(self, colors, length):
        """
        returns np.array of given length that eases between specified colours

        parameters:
        colors - list, colours must be in self.config.colour_manager["colours"]
            eg. ["Red", "Orange", "Blue", "Purple"]
        length - int, length of array to return. should be from self.config.settings
            eg. self.config.settings["devices"]["my strip"]["configuration"]["N_PIXELS"]
        """
        def _easing_func(x, length, slope=2.5):
            # returns a nice eased curve with defined length and curve
            xa = (x/length)**slope
            return xa / (xa + (1 - (x/length))**slope)
        colors = colors[::-1] # needs to be reversed, makes it easier to deal with
        n_transitions = len(colors) - 1
        ease_length = length // n_transitions
        pad = length - (n_transitions * ease_length)
        output = np.zeros((4, length))
        ease = np.array([_easing_func(i, ease_length, slope=2.5) for i in range(ease_length)])
        # for r,g,b,w
        for i in range(4):
            # for each transition
            for j in range(n_transitions):
                # Starting ease value
                start_value = colors[j][i]
                # Ending ease value
                end_value = colors[j+1][i]
                # Difference between start and end
                diff = end_value - start_value
                # Make array of all start value
                base = np.empty(ease_length)
                base.fill(start_value)
                # Make array of the difference between start and end
                diffs = np.empty(ease_length)
                diffs.fill(diff)
                # run diffs through easing function to make smooth curve
                eased_diffs = diffs * ease
                # add transition to base values to produce curve from start to end value
                base += eased_diffs
                # append this to the output array
                output[i, j*ease_length:(j+1)*ease_length] = base
        # cast to int
        output = np.asarray(output, dtype=int)
        # pad out the ends (bit messy but it works and looks good)
        if pad:
            for i in range(4):
                output[i, -pad:] = output[i, -pad-1]
        return output

    def colour(self, colour):
        # returns the values of a given colour. use this function to get colour values.
        if colour in self._config["colours"]:
            return self._config["colours"][colour]
        else:
            print("colour {} has not been defined".format(colour))
            return (0,0,0,0)

    def build_slidearrays(self):
        led_count = self._config["device_config"]["LED_Count"]        

        self.full_slide = {}

        for gradient in self._config["gradients"]:
            for color in self._config["gradients"][gradient]:
                # Fill the whole strip with the color.
                currentColorArray = np.array([
                    [color[0] for i in range(led_count)],
                    [color[1] for i in range(led_count)],
                    [color[2] for i in range(led_count)],
                    [color[3] for i in range(led_count)]
                ])

                if not gradient in self.full_slide:
                    self.full_slide[gradient] = currentColorArray
                    
                else:
                    self.full_slide[gradient] = np.concatenate((self.full_slide[gradient], currentColorArray), axis=1)

    def build_bubblearrays(self):
        led_count = self._config["device_config"]["LED_Count"]        
        effect_config = self._config["effects"]["effect_bubble"]

        self.full_bubble = {}

        for gradient in self._config["gradients"]:
            gradient_color_count  = len(self._config["gradients"][gradient])
            current_color = 1
            
            # Get the steps between each bubble
            steps_between_bubbles = int(led_count / (gradient_color_count * effect_config["bubble_repeat"]))

            # First build black array:
            self.full_bubble[gradient] = np.zeros((4, led_count))

            for color in self._config["gradients"][gradient]:
                
                for current_bubble_repeat in range(effect_config["bubble_repeat"]):

                    #             Find the right spot in the array for the repeat                          Find the right spot in the repeat for the color
                    start_index = int((current_bubble_repeat * gradient_color_count *  steps_between_bubbles) + (current_color * steps_between_bubbles))
                    end_index = int(start_index + effect_config["bubble_lenght"])
                    
                    # If the start reaches the end of the string something is wrong.
                    if start_index > led_count - 1:
                        start_index = led_count - 1

                    # If the range of the strip is reached use the max index.
                    if end_index > led_count - 1:
                        end_index = led_count - 1

                    self.full_bubble[gradient][0][start_index:end_index] = color[0]
                    self.full_bubble[gradient][1][start_index:end_index] = color[1]
                    self.full_bubble[gradient][2][start_index:end_index] = color[2]
                    self.full_bubble[gradient][3][start_index:end_index] = color[3]
                    
                current_color = current_color + 1

            # Build an array, that contains the bubble array three times
            tmp_gradient_array = self.full_bubble[gradient]
            tmp_gradient_array = np.concatenate((tmp_gradient_array, tmp_gradient_array), axis=1)
            tmp_gradient_array = np.concatenate((tmp_gradient_array, tmp_gradient_array), axis=1)

            tmp_gradient_array = gaussian_filter1d(tmp_gradient_array, sigma=effect_config["blur"])

            start_index = led_count - 1
            end_index = start_index  + led_count
            self.full_bubble[gradient] = tmp_gradient_array[:, start_index:end_index]
            



