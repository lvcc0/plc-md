program LatticeGenerator

use iso_fortran_env, only: dp => real64
implicit none

! --- constants --- !
real(dp), parameter :: r2 = sqrt(2.0_dp)
real(dp), parameter :: r3 = sqrt(3.0_dp)
real(dp), parameter :: r6 = sqrt(6.0_dp)

real(dp), parameter :: a_val = 4.05_dp ! lattice constant
real(dp), parameter :: b_val = a_val / r2 ! burgers vector value
! --- !

real(dp) :: t_start, t_end ! timing variables

real(dp) :: cell_atoms(6, 3) ! periodic atom coordinates in a unit cell
real(dp) :: cell_dim(3)      ! unit cell dimensions (oriented unit cell lengths in each dimension)
real(dp) :: box_dim(3, 2)    ! box dimensions (min/max in each dimension)

real(dp), allocatable :: atoms(:, :, :) ! all atom positions

integer :: cell_number(3) ! number of unit cells along each dimension

logical, allocatable :: active_cells(:) ! (PAD) cells to 'render' 

integer :: cells_total ! total number of cells

integer :: i, j, k, l
integer :: cell_counter
integer :: atom_id

integer :: structure_choice

write(*,*) 'This script will generate FCC crystal lattice with orientation:'
write(*,*) ' - X: [110]'
write(*,*) ' - Y: [111]'
write(*,*) ' - Z: [112]'
write(*,*) 'Considering a=4.05 (Al).'

! atom positions in the reference unit cell
cell_atoms(1,1) = a_val/2.0_dp/r2
cell_atoms(1,2) = 0.0_dp
cell_atoms(1,3) = a_val*3.0_dp/2.0_dp/r6

cell_atoms(2,1) = a_val/2.0_dp/r2
cell_atoms(2,2) = a_val/r3
cell_atoms(2,3) = a_val*5.0_dp*r6/12.0_dp

cell_atoms(3,1) = 0.0_dp
cell_atoms(3,2) = 0.0_dp
cell_atoms(3,3) = 0.0_dp

cell_atoms(4,1) = 0.0_dp
cell_atoms(4,2) = a_val/r3
cell_atoms(4,3) = a_val/r6

cell_atoms(5,1) = a_val/2.0_dp/r2
cell_atoms(5,2) = a_val*2.0_dp/r3
cell_atoms(5,3) = a_val/2.0_dp/r6

cell_atoms(6,1) = 0.0_dp
cell_atoms(6,2) = a_val*2.0_dp/r3
cell_atoms(6,3) = a_val*2.0_dp/r6

! size of the unit cell
cell_dim(1) = a_val/r2
cell_dim(2) = a_val*r3
cell_dim(3) = a_val*3.0_dp/r6

write(*,*) 'number of unit cells along X, Y, Z:'
write(*,*) '(!) X - odd, Y - even, Z - any'
read(*,*) cell_number(1), cell_number(2), cell_number(3)

cells_total = cell_number(1) * cell_number(2) * cell_number(3)

! (1) -> "cell id" \in [1, cells_total]
! (2) -> "atom id in a unit cell" \in [1, 6]
! (3) -> "global atom coordinate" (x, y, z)
allocate(atoms(cells_total, 6, 3))

! generate all atomic positions
cell_counter = 0
do i=1, cell_number(1)         ! x
    do j=1, cell_number(2)     ! y
        do k=1, cell_number(3) ! z
            cell_counter = cell_counter + 1
            do l=1, 6
                atoms(cell_counter, l, 1) = cell_atoms(l, 1) + (i-1) * cell_dim(1)
                atoms(cell_counter, l, 2) = cell_atoms(l, 2) + (j-1) * cell_dim(2)
                atoms(cell_counter, l, 3) = cell_atoms(l, 3) + (k-1) * cell_dim(3)
            end do
        end do
    end do
end do

write(*,*) 'What kind of crystal structure to generate?'
write(*,*) '1. Perfect FCC'
write(*,*) '2. PAD (Periodic Array of Dislocations)'
read(*,*)  structure_choice

call cpu_time(t_start)

select case (structure_choice)

case(1) ! "Perfect FCC"
    write(*,*) 'Writing "Perfect FCC" atom data to "atoms.perfect"...'

    box_dim = 0.0_dp
    box_dim(1, 2) = cell_number(1) * cell_dim(1)
    box_dim(2, 2) = cell_number(2) * cell_dim(2)
    box_dim(3, 2) = cell_number(3) * cell_dim(3)

    ! write actual data to the file (LAMMPS formatting)
    open(1, file='atoms.perfect', status='replace')
    write(1,*) 'Position data for Al File'
    write(1,*)
    write(1,*) cells_total * 6, 'atoms'
    write(1,*) '1 atom types'
    write(1,*) box_dim(1, 1:2), 'xlo xhi'
    write(1,*) box_dim(2, 1:2), 'ylo yhi'
    write(1,*) box_dim(3, 1:2), 'zlo zhi'
    write(1,*)
    write(1,*) 'Atoms'
    write(1,*)

    atom_id = 1
    cell_counter = 0
    do i=1, cell_number(1)         ! x
        do j=1, cell_number(2)     ! y
            do k=1, cell_number(3) ! z
                cell_counter = cell_counter + 1
                do l=1, 6
                    write(1,10) atom_id, 1, atoms(cell_counter, l, 1:3)
                    atom_id = atom_id + 1
                end do
            end do
        end do
    end do

    close(1)

case(2) ! "PAD"
    write(*,*) 'Writing "PAD" atom data to "atoms.pad"...'

    allocate(active_cells(cells_total))
    active_cells = .true.

    ! removing half-plane of atoms from the right edge
    ! (starting counting from the last vertical Oyz plane)
    cell_counter = cell_number(3) * cell_number(2) * (cell_number(1) - 1)
    do j=1, cell_number(2)     ! y
        do k=1, cell_number(3) ! z
            cell_counter = cell_counter + 1
            if (j <= cell_number(2) / 2) then
                active_cells(cell_counter) = .false.
            end if
        end do
    end do

    cell_counter = 0
    do i=1, cell_number(1)         ! x
        do j=1, cell_number(2)     ! y
            do k=1, cell_number(3) ! z
                cell_counter = cell_counter + 1
                do l=1, 6
                    if (j <= cell_number(2) / 2) then
                        atoms(cell_counter, l, 1) = atoms(cell_counter, l, 1) * (1.0_dp + 0.5_dp * b_val / (cell_number(1)-1) / cell_dim(1))
                    else
                        atoms(cell_counter, l, 1) = atoms(cell_counter, l, 1) * (1.0_dp - 0.5_dp * b_val / (cell_number(1)-1) / cell_dim(1))
                    end if
                end do
            end do
        end do
    end do

    box_dim = 0.0_dp
    box_dim(1, 2) = (cell_number(1)-1) * cell_dim(1) + b_val * 0.5_dp
    box_dim(2, 2) = cell_number(2) * cell_dim(2)
    box_dim(3, 2) = cell_number(3) * cell_dim(3)

    ! write actual data to the file (LAMMPS formatting)
    open(1, file='atoms.pad', status='replace')
    write(1,*) 'Position data for Al File'
    write(1,*)
    write(1,*) (cells_total - cell_number(3) * cell_number(2) / 2) * 6, 'atoms'
    write(1,*) '1 atom types'
    write(1,*) box_dim(1, 1:2), ' xlo xhi'
    write(1,*) box_dim(2, 1:2), ' ylo yhi'
    write(1,*) box_dim(3, 1:2), ' zlo zhi'
    write(1,*)
    write(1,*) 'Atoms'
    write(1,*)

    atom_id = 1
    cell_counter = 0
    do i=1, cell_number(1)         ! x
        do j=1, cell_number(2)     ! y
            do k=1, cell_number(3) ! z
                cell_counter = cell_counter + 1
                do l=1, 6
                    if (active_cells(cell_counter)) then
                        write(1,10) atom_id, 1, atoms(cell_counter, l, 1:3)
                        atom_id = atom_id + 1
                    endif
                end do
            end do
        end do
    end do

    close(1)

end select

call cpu_time(t_end)

write(*,'(A, F8.4, A)') 'Total time elapsed:', t_end - t_start, ' sec'

10 format(i8, i8, 3(1x, e12.5))

end program
