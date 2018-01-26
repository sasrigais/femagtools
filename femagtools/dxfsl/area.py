# -*- coding: utf-8 -*-
"""manage a geometry with
    lines, circles and arcs built from DXF

  NOTE: This code is in highly experimental state.
        Use at your own risk.

  Author: Ronald Tanner
    Date: 2017/07/06
"""
from __future__ import print_function
import numpy as np
import networkx as nx
import logging
from .functions import less_equal, less, greater_equal, greater
from .functions import distance, alpha_angle, min_angle, max_angle
from .functions import point, line_m, line_n, intersect_point
from .functions import middle_angle, part_of_circle
from .shape import Element, Shape, Line

logger = logging.getLogger('femagtools.area')


#############################
#            Area           #
#############################

class Area(object):
    def __init__(self, area, center, sym_tolerance):
        self.area = area
        self.type = 0  # material
        self.min_angle = 0.0
        self.max_angle = 0.0
        self.close_to_startangle = False
        self.close_to_endangle = False
        self.min_dist = 99999.0
        self.max_dist = 0.0
        self.alpha = 0.0
        self.count = 1
        self.equal_areas = []
        self.delta = 0.0
        self.start = 0.0
        self.sym_startangle = 0.0
        self.sym_endangle = 0.0
        self.sym_type = 0
        self.symmetry = 0
        self.sym_tolerance = sym_tolerance
        self.calc_signature(center)

    def number_of_elements(self):
        return len(self.area)

    def elements(self):
        return self.area

    def nodes(self):
        if len(self.area) == 0:
            return

        for e in self.area:
            yield e.p1
            yield e.p2

    def name(self):
        if self.type == 1:
            return 'iron'
        if self.type == 2:
            return 'windings'
        if self.type == 3 or self.type == 4:
            return 'magnet'
        return 'unknown'

    def color(self):
        if self.type == 1:
            return 'blue'
        if self.type == 2:
            return 'green'
        if self.type == 3 or self.type == 4:
            return 'red'
        return 'magenta'

    def calc_signature(self, center):
        if not self.area:
            return

        s = self.area[0]
        mm_angle = s.minmax_angle_from_center(center)
        self.min_angle = mm_angle[0]
        self.max_angle = mm_angle[1]

        for s in self.area:
            mm_dist = s.minmax_from_center(center)
            self.min_dist = min(self.min_dist, mm_dist[0])
            self.max_dist = max(self.max_dist, mm_dist[1])

            mm_angle = s.minmax_angle_from_center(center)
            self.min_angle = min_angle(self.min_angle, mm_angle[0])
            self.max_angle = max_angle(self.max_angle, mm_angle[1])

        self.alpha = round(alpha_angle(self.min_angle, self.max_angle), 3)

    def minmax_angle_dist_from_center(self, center, dist):
        s = self.area[0]
        my_min_angle = self.max_angle
        my_max_angle = self.min_angle
        mm_angle = None
        for s in self.area:
            mm_angle = s.minmax_angle_dist_from_center(center, dist)
            if mm_angle:
                my_min_angle = min_angle(my_min_angle, mm_angle[0])
                my_max_angle = max_angle(my_max_angle, mm_angle[1])
        return (my_min_angle, my_max_angle)

    def is_inside(self, area):
        if less_equal(area.min_dist, self.min_dist):
            return False
        if greater_equal(area.max_dist, self.max_dist):
            return False
        if less_equal(area.min_angle, self.min_angle):
            return False
        if greater_equal(area.max_angle, self.max_angle):
            return False
        return True

    def has_connection(self, geom, a, ndec):
        assert(self.area)
        assert(a.area)
        n1 = self.area[0].node1(ndec)
        if not geom.g.has_node(n1):
            n = geom.find_nodes(n1)
            if not n:
                logger.warn("FATAL: node {} not available".format(n1))
                return False
            n1 = n[0]

        n2 = a.area[0].node2(ndec)
        if not geom.g.has_node(n2):
            n = geom.find_nodes(n2)
            if not n:
                logger.warn("FATAL: node {} not available".format(n2))
                return False
            n2 = n[0]

        try:
            return nx.has_path(geom.g, n1, n2)
        except nx.NetworkXError:
            logger.warn("has_path() failed")
            return False

    def get_most_left_point(self, center, radius, angle):
        axis_p = point(center, radius, angle)
        axis_m = line_m(center, axis_p)
        axis_n = line_n(center, axis_m)

        the_area_p = None
        the_axis_p = None
        dist = 99999
        for n in self.nodes():
            p = intersect_point(n, center, axis_m, axis_n)
            d = distance(n, p)
            if d < dist:
                dist = d
                the_area_p = n
                the_axis_p = p

        return (dist, the_axis_p, the_area_p)

    def is_equal(self, a, sym_tolerance):
        if sym_tolerance > 0.0:
            if np.isclose(round(self.min_dist, 4),
                          round(a.min_dist, 4),
                          1e-03, sym_tolerance) and \
               np.isclose(round(self.max_dist, 4),
                          round(a.max_dist, 4),
                          1e-03, sym_tolerance) and \
               np.isclose(round(self.alpha, 3),
                          round(a.alpha, 3),
                          1e-02, 0.001):
                return True
        else:
            if np.isclose(round(self.min_dist, 2),
                          round(a.min_dist, 2)) and \
               np.isclose(round(self.max_dist, 2),
                          round(a.max_dist, 2)) and \
               np.isclose(round(self.alpha, 3),
                          round(a.alpha, 3), 1e-02, 0.001):
                return True
        return False

    def is_identical(self, area):
        if np.isclose(self.min_dist, area.min_dist) and \
           np.isclose(self.max_dist, area.max_dist) and \
           np.isclose(self.alpha, area.alpha) and \
           np.isclose(self.min_angle, area.min_angle) and \
           np.isclose(self.max_angle, area.max_angle):
            return True
        return False

    def increment(self, a):
        if self.is_identical(a):
            return

        for area in self.equal_areas:
            if area.is_identical(a):
                return

        self.count += 1
        self.equal_areas.append(a)

    def set_delta(self):
        self.delta = 0.0
        self.symmetry = 0

        if len(self.equal_areas) < 2:
            # Mit zwei Objekten lässt sich das Teil nur noch halbieren. Das
            # wird zum Schluss sowieso versucht.
            return

        a_prev = self
        delta = {}
        for a in self.equal_areas:
            d = round(alpha_angle(a_prev.min_angle, a.min_angle), 2)
            if d in delta:
                delta[d] += 1
            else:
                delta[d] = 1
            a_prev = a

        delta_sorted = list([v, k] for (k, v) in delta.items())

        if len(delta_sorted) == 1:
            # simple case: all have the same angle
            self.delta = alpha_angle(self.min_angle,
                                     self.equal_areas[0].min_angle)
            self.start = middle_angle(self.max_angle,
                                      self.equal_areas[0].min_angle)
            self.sym_type = 3
            self.symmetry = part_of_circle(0.0, self.delta, 1)
            return

        if len(delta_sorted) > 2:
            # Mehr als 2 Winkel untersuchen wir (noch) nicht. Wir brechen
            # die Suche nach dem richtigen Winkel ab.
            return

        # Bei 2 verschiedenen Winkeln werden die näher beieinander liegenden
        # Objekte zusammen genommen.

        if len(self.equal_areas) < 4:
            # Wenn nicht mehr als 4 Objekte vorhanden sind, brechen wir auch
            # ab.
            return

        percent = delta_sorted[0][0] / (len(self.equal_areas)+1)
        if percent > 0.75:
            # lets assume we only have on angle
            self.delta = alpha_angle(self.min_angle,
                                     self.equal_areas[0].min_angle)
            self.start = middle_angle(self.max_angle,
                                      self.equal_areas[0].min_angle)
            self.sym_type = 2
            self.symmetry = part_of_circle(0.0, self.delta, 1)
            return

        # Lets hope the distances are changing
        self.delta = alpha_angle(self.min_angle, self.equal_areas[1].min_angle)
        self.sym_type = 1
        self.symmetry = part_of_circle(0.0, self.delta, 1)

        delta_1 = alpha_angle(self.min_angle,
                              self.equal_areas[0].min_angle)
        delta_2 = alpha_angle(self.equal_areas[0].min_angle,
                              self.equal_areas[1].min_angle)

        if np.isclose(delta_1, delta_2):
            # Hm. the distances are not changing
            self.delta = 0.0
            return

#        print(" = delta_1={}, delta_2={}".format(delta_1, delta_2))

        if delta_1 < delta_2:
            self.start = middle_angle(self.equal_areas[0].max_angle,
                                      self.equal_areas[1].min_angle)
        else:
            self.start = middle_angle(self.max_angle,
                                      self.equal_areas[0].min_angle)

    def symmetry_lines(self, startangle, endangle):
        if less_equal(endangle, startangle):
            endangle += 2*np.pi

        angle = self.start
        while less(angle, startangle):
            angle += self.delta
        while greater(angle, startangle+self.delta):
            angle -= self.delta

        # Damit man anschliessend ohne Umstände schneiden kann.
        self.sym_startangle = angle
        self.sym_endangle = angle + self.delta

        while angle < endangle:
            yield angle
            angle += self.delta

    def minmax(self):
        mm = [99999, -99999, 99999, -99999]

        for e in self.area:
            n = e.minmax()
            mm[0] = min(mm[0], n[0])
            mm[1] = max(mm[1], n[1])
            mm[2] = min(mm[2], n[2])
            mm[3] = max(mm[3], n[3])
        return mm

    def get_point_inside(self, geom):
        """return point inside area"""
        mm = self.minmax()
        y = (mm[2]+mm[3])/2
        p1 = (mm[0]-5, y)
        p2 = (mm[1]+5, y)
        line = Line(Element(start=p1, end=p2))

        points = []
        for e in self.area:
            points += e.intersect_line(line, geom.rtol, geom.atol, True)

        if len(points) < 2:
            logger.debug("WARNING: get_point_inside() failed ({})".
                         format(len(points)))
            return None

        assert(len(points) > 1)

        points_sorted = []
        for p in points:
            points_sorted.append((p[0], p))
        points_sorted.sort()
        p1 = points_sorted[0][1]  # Startpoint

        points_sorted = []
        for e in geom.elements(Shape):
            points = e.intersect_line(line, geom.rtol, geom.atol, True)
            for p in points:
                if p[0] > p1[0]:
                    points_sorted.append((p[0], p))
        points_sorted.sort()

        p2 = points_sorted[0][1]
        return ((p1[0]+p2[0])/2, y)

    def render(self, renderer, color='black', with_nodes=False):
        for e in self.area:
            e.render(renderer, color, with_nodes)
        return

    def remove_edges(self, g, ndec):
        for e in self.area:
            try:
                g.remove_edge(e.node1(ndec), e.node2(ndec))
            except Exception:
                continue

    def is_rectangle(self):
        lines = []
        for c, e in enumerate(self.area):
            if isinstance(e, Line):
                l = e.length()
                m = e.m()
                if m is None:
                    m = 99999.0
                lines.append((c, m, l))

        lines.sort()
        line_count = 1
        m_prev = 999.999999
        c_prev = -99
        for c, m, l in lines:
            if c_prev >= 0:
                if np.isclose(m_prev, m):
                    if c_prev+1 != c:
                        # Gleiche Steigung, aber keine Verlängerung
                        line_count += 1
                else:
                    line_count += 1

            m_prev = m
            c_prev = c

        return line_count == 4

    def mark_stator_subregions(self, is_inner, mirrored, alpha,
                               center, r_in, r_out):
        alpha = round(alpha, 6)

        if is_inner:
            close_to_ag = np.isclose(r_out, self.max_dist)
            close_to_opposition = np.isclose(r_in, self.min_dist)
            airgap_radius = r_out
        else:
            close_to_ag = np.isclose(r_in, self.min_dist)
            close_to_opposition = np.isclose(r_out, self.max_dist)
            airgap_radius = r_in

        self.close_to_startangle = np.isclose(self.min_angle, 0.0)
        self.close_to_endangle = np.isclose(self.max_angle, alpha)

        if self.close_to_startangle and self.close_to_endangle:
            self.type = 1  # iron
            return self.type

        if close_to_opposition:
            self.type = 1  # iron
            return self.type

        if close_to_ag:  # close to airgap
            mm = self.minmax_angle_dist_from_center(center, airgap_radius)
            air_alpha = round(alpha_angle(mm[0], mm[1]), 3)
            if air_alpha / alpha < 0.2:
                self.type = 0  # air
                return self.type
            else:
                self.type = 1  # iron
            return self.type

        if self.min_angle > 0.001:
            if self.max_angle < alpha - 0.001:
                self.type = 2  # windings
            elif mirrored:
                self.type = 2  # windings
            else:
                self.type = 0  # air
            return self.type

        return 0

    def mark_rotor_subregions(self, is_inner, mirrored, alpha,
                              center, r_in, r_out):
        my_alpha = round(self.max_angle - self.min_angle, 6)
        alpha = round(alpha, 6)

        if is_inner:
            close_to_ag = np.isclose(r_out, self.max_dist)
            close_to_opposition = np.isclose(r_in, self.min_dist)
            airgap_radius = r_out
        else:
            close_to_ag = np.isclose(r_in, self.min_dist)
            close_to_opposition = np.isclose(r_out, self.max_dist)
            airgap_radius = r_in

        self.close_to_startangle = np.isclose(self.min_angle, 0.0)
        self.close_to_endangle = np.isclose(self.max_angle, alpha)

        if close_to_opposition:
            self.type = 1  # iron
            return self.type

        if close_to_ag:
            mm = self.minmax_angle_dist_from_center(center, airgap_radius)
            air_alpha = round(alpha_angle(mm[0], mm[1]), 3)
            if air_alpha / alpha < 0.2:
                self.type = 0  # air
                return self.type

            if air_alpha / alpha > 0.6:
                self.type = 3  # magnet
            else:
                self.type = 1  # iron
            return self.type

        if my_alpha / alpha > 0.5:
            if self.is_rectangle():
                self.type = 4  # magnet
                return self.type

        self.type = 1  # iron
        if self.min_angle > 0.001:
            if my_alpha / alpha < 0.4:
                if self.max_angle < alpha - 0.001:
                    self.type = 0  # air
                elif mirrored:
                    self.type = 0  # air

        return self.type

    def print_area(self):
        center = [0.0, 0.0]
        for s in self.area:
            mm = s.minmax_angle_from_center(center)
            print(" --- angle min={}, max={}".format(mm[0], mm[1]))

    def __lt__(self, a):
        if self.symmetry != a.symmetry:
            return self.symmetry > a.symmetry

        if self.sym_type != a.sym_type:
            return self.sym_type > a.sym_type

        if self.count != a.count:
            return self.count > a.count

        if self.sym_tolerance > 0.0:
            if not np.isclose(round(self.min_dist, 4),
                              round(a.min_dist, 4), 1e-03,
                              self.sym_tolerance):
                return less_equal(self.min_dist, a.min_dist)
            if not np.isclose(round(self.max_dist, 4),
                              round(a.max_dist, 4), 1e-03,
                              self.sym_tolerance):
                return less_equal(self.max_dist, a.max_dist)
            if not np.isclose(round(self.alpha, 2),
                              round(a.alpha, 2), 1e-01, 1e-01):
                return less_equal(self.alpha, a.alpha)
        else:
            if not np.isclose(round(self.min_dist, 2),
                              round(a.min_dist, 2)):
                return less_equal(self.min_dist, a.min_dist)
            if not np.isclose(round(self.max_dist, 2),
                              round(a.max_dist, 2)):
                return less_equal(self.max_dist, a.max_dist)
            if not np.isclose(round(self.alpha, 2),
                              round(a.alpha, 2), 1e-01, 1e-02):
                return less_equal(self.alpha, a.alpha)

        return self.min_angle < a.min_angle

    def __str__(self):
        return "Area\n distance: from {} to {}\n".\
            format(round(self.min_dist, 4), round(self.max_dist, 4)) + \
            "alpha...: {}\n".format(self.alpha) + \
            "angle...: from {} to {}\n".format(round(self.min_angle, 6),
                                               round(self.max_angle, 6))