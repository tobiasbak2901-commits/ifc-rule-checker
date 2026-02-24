from viewer.model_payload import _triangles_from_faces


def test_triangles_from_faces_supports_flattened_coordinate_indices():
    n_verts = 4
    # Coordinate indices (0,3,6,9) should map to vertex indices (0,1,2,3).
    faces = (0, 3, 6, 0, 6, 9)

    tris = _triangles_from_faces(faces, n_verts)

    assert tris
    assert tris[0] == (0, 1, 2)


def test_triangles_from_faces_supports_one_based_indices():
    n_verts = 4
    faces = (1, 2, 3, 1, 3, 4)

    tris = _triangles_from_faces(faces, n_verts)

    assert tris == [(0, 1, 2), (0, 2, 3)]
